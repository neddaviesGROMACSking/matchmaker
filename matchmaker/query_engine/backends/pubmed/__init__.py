from asyncio import gather, get_running_loop
from copy import copy, deepcopy
from dataclasses import replace
from pprint import pprint
from typing import Annotated, Awaitable, Callable, Dict, List, Tuple, Union

from aiohttp import ClientSession
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.backends import (
    BaseAuthorSearchQueryEngine,
    BaseBackendQueryEngine,
    BasePaperSearchQueryEngine,
    NewAsyncClient,
    RateLimiter,
)
from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError
from matchmaker.query_engine.backends.pubmed.api import (
    MeshTopic,
    PubmedAuthor,
    PubmedEFetchData,
    PubmedEFetchQuery,
    PubmedELinkQuery,
    PubmedESearchQuery,
    PubmedIndividual,
    efetch_on_id_list,
    elink_on_id_list,
    esearch_on_query,
)
from matchmaker.query_engine.backends.pubmed.processors import (
    ProcessedAuthor,
    ProcessedData,
    ProcessedEFetchData,
    ProcessedIndividual,
    process_institution,
)
from matchmaker.query_engine.backends.tools import replace_dict_tags, replace_ids
from matchmaker.query_engine.data_types import AuthorData, BasePaperData, PaperData
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery
from matchmaker.query_engine.query_types import (
    Abstract,
    And,
    AuthorName,
    Institution,
    Journal,
    Keyword,
    Or,
    StringPredicate,
    Title,
    Year,
)
from matchmaker.query_engine.selector_types import (
    PaperDataAllSelected,
    PaperDataSelector,
    SubPaperDataAllSelected,
    SubPaperDataSelector,
    AuthorDataSelector
)
from pydantic import BaseModel, Field
from pydantic.error_wrappers import ValidationError
# TODO Use generators to pass information threough all levels

and_int = And['PubMedAuthorSearchQuery']
or_int = Or['PubMedAuthorSearchQuery']

class PubMedAuthorSearchQuery(BaseModel):
    __root__: Annotated[
    Union[
        and_int,
        or_int,
        AuthorName,
        Institution,
        MeshTopic
    ],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()
PubMedAuthorSearchQuery.update_forward_refs()

class PubmedNativeData(PubmedEFetchData):
    references: List[PubmedEFetchData] = []
    cited_by: List[PubmedEFetchData] = []


class ProcessedAuthorData(BaseModel):
    author: ProcessedAuthor
    papers: List[PubmedNativeData]
    paper_count: int


def paper_from_native(data):
    raise NotImplementedError('TODO')



def make_doi_search_term(doi_list):
    new_doi_list = [doi + '[Location ID]' for doi in doi_list]
    return ' OR '.join(new_doi_list)



def paper_query_to_esearch(query: PaperSearchQuery):
    # TODO convert topic to elocation
    # convert id.pubmed to pmid
    # convert id.doi to elocation
    #new_query_dict = replace_ids(query.dict()['__root__'])
    new_query_dict = query.dict()['query']
    new_query_dict = replace_dict_tags(
        new_query_dict,
        elocationid = 'doi'
    )
    try:
        return PubmedESearchQuery.parse_obj(new_query_dict)
    except ValidationError as e:
        raise QueryNotSupportedError(e.raw_errors)
def author_query_to_esearch(query: AuthorSearchQuery):
    # TODO convert topic to elocation
    # convert id.pubmed to pmid
    # convert id.doi to elocation
    return PubmedESearchQuery.parse_obj(query.dict()['query'])

async def process_paper_institutions(i):
    async def process_authors(authors):
        new_authors = []
        for author in authors:
            inst = author.__root__.institution
            if inst is not None:
                proc_inst = process_institution(inst)
            else:
                proc_inst = None
            if isinstance(author.__root__, PubmedIndividual):
                new_author = ProcessedAuthor.parse_obj({
                    **author.dict()['__root__'],
                    'proc_institution': proc_inst
                })
            else:
                new_author = ProcessedAuthor.parse_obj({
                    **author.dict()['__root__'],
                    'proc_institution': proc_inst
                })
            new_authors.append(new_author)
        return new_authors
    authors = i.author_list
    new_authors = await process_authors(authors)
    refs = i.references
    cited_by = i.cited_by
    new_refs = []
    if refs is not None:
        for j in refs:
            refs_authors = j.author_list
            new_refs_authors = await process_authors(refs_authors)
            new_ref = ProcessedEFetchData.parse_obj({**j.dict(), 'author_list': new_refs_authors})
            new_refs.append(new_ref)
    new_citeds = []
    if cited_by is not None:
        for j in cited_by:
            cited_authors = j.author_list
            new_cited_authors = await process_authors(cited_authors)
            new_cited = ProcessedEFetchData.parse_obj({**j.dict(), 'author_list': new_cited_authors})
            new_citeds.append(new_cited)
    i_dict = i.dict()
    i_dict['author_list'] = new_authors
    i_dict['references'] = new_refs
    i_dict['cited_by'] = new_citeds
    return ProcessedData.parse_obj(i_dict)



class PaperSearchQueryEngine(
        BasePaperSearchQueryEngine[List[PubmedNativeData]]):
    api_key:str
    def __init__(self, api_key, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        self.api_key = api_key
        esearch_field_bools = {'paper_id':{'pubmed_id':True}}
        efetch_field_bools = {
            'paper_id': {
                'pubmed_id': True,
                'doi': True
            },
            'title': True,
            'authors': {
                'preferred_name': True,
                'institution_current': {
                    'name': True,
                    'processed': True
                }
            },
            'year': True,
            'source_title': True,
            'source_title_abr': True,
            'abstract': True,
            'keywords': True,
            'topics': True
        }
        esearch_fields = PaperDataSelector.parse_obj(esearch_field_bools)
        esearch_efetch_fields = PaperDataSelector.parse_obj(efetch_field_bools)
        esearch_elink_refs_fields = PaperDataSelector.parse_obj({
            **esearch_field_bools,
            'references': esearch_field_bools
        })
        esearch_elink_citeds_fields = PaperDataSelector.parse_obj({
            **esearch_field_bools,
            'cited_by': esearch_field_bools
        })
        self.possible_searches = [
            esearch_fields,
            esearch_efetch_fields,
            esearch_elink_refs_fields,
            esearch_elink_citeds_fields
        ]
        self.available_fields = PaperDataSelector.parse_obj({
            **efetch_field_bools,
            'references': efetch_field_bools,
            'cited_by': efetch_field_bools
        })
        super().__init__(rate_limiter, *args, **kwargs)

    async def _query_to_awaitable(self, query: PaperSearchQuery, client: NewAsyncClient) -> Tuple[
        Callable[
            [NewAsyncClient], 
            Awaitable[List[PubmedNativeData]]
        ], 
        Dict[str,int]
    ]:
        split_factor = 9
        metadata = {
            'efetch': 1+split_factor,
            'esearch': 1,
            'elink': 2
        }
        if query.selector in self.available_fields:
            # TODO Optimise requests based on fields selected
            pass
        else:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        pubmed_search_query = paper_query_to_esearch(query)

        async def make_coroutine(client: ClientSession) -> List[PubmedNativeData]:
            async def esearch_on_query_set_future(id_list_future, query, client):

                output = await esearch_on_query(query, client, api_key=self.api_key)
                id_list = output.pubmed_id_list
                id_list_future.set_result(id_list)
                return id_list_future
            
            async def efetch_on_id_list_resolve_id(id_list_future, client):
                await id_list_future
                id_list = id_list_future.result()
                result = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = id_list), client, api_key=self.api_key)
                return result

            async def efetch_on_elink_resolve_id(id_list_future, fetch_list_future, linkname, client):
                def id_mapper_to_unique_list(id_mapper):
                    unique_ids = []
                    for start_id, linked_ids in id_mapper.items():
                        if linked_ids is not None:
                            for linked_id in linked_ids:
                                if linked_id not in unique_ids:
                                    unique_ids.append(linked_id)
                    return unique_ids
                
                await id_list_future
                id_list = id_list_future.result()

                output = await elink_on_id_list(PubmedELinkQuery(pubmed_id_list = id_list, linkname = linkname), client, api_key=self.api_key)
                
                id_mapper = output.id_mapper
                unique_fetch_list = id_mapper_to_unique_list(id_mapper)
                fetch_list_future.set_result(unique_fetch_list)
                return id_mapper

            async def redistribute_fetches(*list_futures, bin_futures = None, split_factor = None):
                if bin_futures is None:
                    raise ValueError( 'No bin_futures')
                if split_factor is None:
                    raise ValueError('No split factor')
                
                total_fetch_list = []
                for i in list_futures:
                    await i
                    fetch_list = i.result()
                    total_fetch_list += fetch_list
                unique_total_fetch_list = list(set(total_fetch_list))
                fetch_length = len(unique_total_fetch_list)
                bin_size = fetch_length // split_factor
                bins = []
                for i in range(split_factor):
                    if i == split_factor -1:
                        bins.append(unique_total_fetch_list[bin_size*i:len(unique_total_fetch_list)])
                    else:
                        bins.append(unique_total_fetch_list[bin_size*i:bin_size*(i+1)])

                for counter, j in enumerate(bin_futures):
                    bin_item = bins[counter]
                    j.set_result(bin_item)
            
            async def get_papers_from_index(id_mapper, sub_paper_index):
                id_mapper_papers = {}
                for search_id, id_list in id_mapper.items():
                    if id_list is not None:
                        id_mapper_papers[search_id] = [sub_paper_index[sub_id] for sub_id in id_list]
                    else:
                        id_mapper_papers[search_id] = []
                return id_mapper_papers
            
            original_fetch_ids_future = get_running_loop().create_future()
            ref_fetch_list_future = get_running_loop().create_future()
            cited_fetch_list_future = get_running_loop().create_future()

            bin_futures = []
            for j in range(split_factor):
                bin_futures.append(get_running_loop().create_future())
            
            awaitables = []

            esearch_await = esearch_on_query_set_future(original_fetch_ids_future, pubmed_search_query, client)
            efetch_await = efetch_on_id_list_resolve_id(original_fetch_ids_future, client)

            references_set_await = efetch_on_elink_resolve_id(
                original_fetch_ids_future,
                ref_fetch_list_future,
                'pubmed_pubmed_refs', 
                client
            )
            cited_by_set_await = efetch_on_elink_resolve_id(
                original_fetch_ids_future, 
                cited_fetch_list_future, 
                'pubmed_pubmed_citedin', 
                client
            )

            redistribute_await = redistribute_fetches(
                ref_fetch_list_future, 
                cited_fetch_list_future, 
                bin_futures = bin_futures,
                split_factor=split_factor
            )
            awaitables += [esearch_await, efetch_await, references_set_await, cited_by_set_await, redistribute_await]
            for i in bin_futures:
                awaitables.append(efetch_on_id_list_resolve_id(i,client))

            gather_output = await gather(
                *awaitables
            )
            listed_gather_out = list(gather_output)
            esearch_out, papers, references_mapper, cited_by_mapper, redist_out = listed_gather_out[0:5]
            sub_papers = listed_gather_out[5: len(listed_gather_out)]
            new_sub_papers = []
            for i in sub_papers:
                new_sub_papers += i
            
            sub_paper_index = {i.paper_id.pubmed: i for i in new_sub_papers}
            references_set, cited_by_set = await gather(
                get_papers_from_index(references_mapper, sub_paper_index),
                get_papers_from_index(cited_by_mapper, sub_paper_index)
            )
            native_papers = []
            for paper in papers:
                pubmed_id = paper.paper_id.pubmed
                native_paper = PubmedNativeData.parse_obj({
                    **paper.dict(),
                    'references': references_set[pubmed_id],
                    'cited_by': cited_by_set[pubmed_id]
                })
                native_papers.append(native_paper)

            return native_papers

        return make_coroutine, metadata

    async def _post_process(self, query: PaperSearchQuery, data: List[PubmedNativeData]) -> List[PaperData]:
        def process_sub_paper_data(data_dict, selector: SubPaperDataSelector):
            new_data_dict = {}
            doi_selected = SubPaperDataSelector.parse_obj({'paper_id':{'doi':True}})
            pmid_selected = SubPaperDataSelector.parse_obj({'paper_id':{'pubmed_id':True}})
            if any([
                doi_selected in selector,
                pmid_selected in selector
            ]):
                paper_id = {}
                if doi_selected in selector:
                    paper_id['doi'] = data_dict['paper_id']['doi']
                if pmid_selected in selector:
                    paper_id['pubmed_id'] = data_dict['paper_id']['pubmed']

                new_data_dict['paper_id'] = paper_id


            if SubPaperDataSelector(title = True) in selector:
                new_data_dict['title'] = data_dict['title']

            if SubPaperDataSelector(year = True) in selector:
                new_data_dict['year'] = data_dict['year']



            surname_selected = SubPaperDataSelector.parse_obj({
                'authors':{
                    'preferred_name':{
                        'surname': True
                    }
                }
            })
            given_names_selected = SubPaperDataSelector.parse_obj({
                'authors':{
                    'preferred_name':{
                        'given_names': True
                    }
                }
            })
            initials_selected = SubPaperDataSelector.parse_obj({
                'authors':{
                    'preferred_name':{
                        'initials': True
                    }
                }
            })
            current_inst_name_selected = SubPaperDataSelector.parse_obj({
                'authors':{
                    'institution_current':{
                        'name': True
                    }
                }
            })
            current_inst_proc_selected = SubPaperDataSelector.parse_obj({
                'authors':{
                    'institution_current':{
                        'processed': True
                    }
                }
            })

            if any([
                surname_selected in selector,
                given_names_selected in selector,
                initials_selected in selector,
                current_inst_name_selected in selector,
                current_inst_proc_selected in selector
            ]):
                new_authors = []
                for author in data_dict['author_list']:
                    author_root = author
                    new_author = {}
                    if any([
                        surname_selected in selector,
                        given_names_selected in selector,
                        initials_selected in selector,
                    ]):
                        new_name = {}
                        if surname_selected in selector:
                            if 'last_name' in author_root:
                                new_name['surname'] = author_root['last_name']
                            else:
                                new_name['surname'] = author_root['collective_name']
                        if given_names_selected in selector:
                            if 'given_names' in author_root:
                                new_name['given_names'] = author_root['fore_name']
                            else:
                                new_name['given_names'] = None
                        if initials_selected in selector:
                            if 'initials' in author_root:
                                new_name['initials'] = author_root['initials']
                        new_author['preferred_name'] = new_name
                    if any([
                        current_inst_name_selected in selector,
                        current_inst_proc_selected in selector
                    ]):
                        new_institution = {}
                        institution = author_root['institution']
                        if current_inst_name_selected in selector:
                            new_institution['name'] = institution
                        if current_inst_proc_selected in selector:
                            if institution is None:
                                new_institution['processed'] = None
                            else:
                                new_institution['processed'] = process_institution(institution)
                        new_author['institution_current'] = new_institution
                    new_authors += [new_author]
                new_data_dict['authors'] = new_authors

            if SubPaperDataSelector(source_title = True) in selector:
                new_data_dict['source_title'] = data_dict['journal_title']

            if SubPaperDataSelector(source_title_abr = True) in selector:
                new_data_dict['source_title_abr'] = data_dict['journal_title_abr']

            if SubPaperDataSelector(abstract = True) in selector:
                abstract = data_dict['abstract']
                if isinstance(abstract, list):
                    abstract_proc = []
                    for item in abstract:
                        if item['label'] is None and item['nlm_category'] is None:
                            new_item = (None, item['text'])
                        elif item['label'] is None:
                            new_item = (item['nlm_category'], item['text'])
                        elif item['nlm_category'] is None:
                            new_item = (item['label'], item['text'])
                        else:
                            item_title = item['label'] + ';' + item['nlm_category']
                            new_item = (item_title, item['text'])
                        abstract_proc.append(new_item)
                else:
                    abstract_proc = abstract
                new_data_dict['abstract'] = abstract_proc


            qualifier_selected = SubPaperDataSelector.parse_obj({'topics': {'qualifier': True}})
            descriptor_selected = SubPaperDataSelector.parse_obj({'topics': {'descriptor': True}})
            if any([
                qualifier_selected in selector,
                descriptor_selected in selector
            ]):
                new_topics = []
                for topic in data_dict['topics']:
                    new_topic = {}
                    if qualifier_selected in selector:
                        new_topic['qualifier'] = topic['qualifier']
                    if descriptor_selected in selector:
                        new_topic['descriptor'] = topic['descriptor']
                    new_topics += [new_topic]
                new_data_dict['topics'] = new_topics


            if SubPaperDataSelector(keywords = True) in selector:
                new_data_dict['keywords'] = data_dict['keywords']
            return new_data_dict
        selector = query.selector
        model = BasePaperData.generate_model_from_selector(selector)
        sub_paper_selector = SubPaperDataSelector.parse_obj(selector.dict())
        if isinstance(selector.references, bool):
            if selector.references:
                ref_sub_paper_selector = deepcopy(SubPaperDataAllSelected)
            else:
                ref_sub_paper_selector = None
        else:
            ref_sub_paper_selector = SubPaperDataSelector.parse_obj(selector.references.dict())

        if isinstance(selector.cited_by, bool):
            if selector.cited_by:
                cited_sub_paper_selector = deepcopy(SubPaperDataAllSelected)
            else:
                cited_sub_paper_selector = None
        else:
            cited_sub_paper_selector = SubPaperDataSelector.parse_obj(selector.cited_by.dict())
        
        def process_paper_data(data):
            data_dict = data.dict()
            new_data_dict = process_sub_paper_data(data_dict, sub_paper_selector)

            if ref_sub_paper_selector is not None:
                all_except_refs = deepcopy(PaperDataAllSelected)
                all_except_refs.references = False
                # If references is False
                # And everything else is True
                # And selector is not in this
                # something in references must be selected
                if selector not in all_except_refs:
                    new_references = []
                    for j in data_dict['references']:
                        refs_paper_dict = process_sub_paper_data(j, ref_sub_paper_selector)
                        new_references.append(refs_paper_dict)
                    new_data_dict['references'] = new_references
            if cited_sub_paper_selector is not None:
                all_except_refs = deepcopy(PaperDataAllSelected)
                all_except_refs.cited_by = False
                if selector not in all_except_refs:
                    new_cited_bys = []
                    for j in data_dict['cited_by']:
                        cited_by_paper_dict = process_sub_paper_data(data_dict, cited_sub_paper_selector)
                        new_cited_bys.append(cited_by_paper_dict)
                    new_data_dict['cited_by'] = new_cited_bys
            return model.parse_obj(new_data_dict)
        
        new_data = []
        for i in data:
            new_data.append(process_paper_data(i))
        return new_data









class AuthorSearchQueryEngine(
        BaseAuthorSearchQueryEngine[List[PubmedNativeData]]):
        
    def __init__(self, api_key, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        self.api_key = api_key
        self.available_fields = AuthorDataSelector.parse_obj({
            'preferred_name': {
                'surname': True,
                'given_names': True,
                'initials': True
            },

        })
        super().__init__(rate_limiter, *args, **kwargs)

    async def _query_to_awaitable(self, query: AuthorSearchQuery, client: NewAsyncClient) -> Tuple[
        Callable[
            [NewAsyncClient], 
            Awaitable[List[PubmedNativeData]]
        ], 
        Dict[str,int]
    ]:
        async def make_coroutine(client: ClientSession) -> List[PubmedNativeData]:
            pubmed_paper_query = author_query_to_esearch(query)
            output = await esearch_on_query(pubmed_paper_query, client, api_key=self.api_key)
            id_list = output.pubmed_id_list
            output = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = id_list), client, api_key = self.api_key)

            native = [PubmedNativeData.parse_obj(i.dict()) for i in output]
            return native
        metadata = {
            'efetch': 1,
            'esearch': 1
        }
        return make_coroutine, metadata


    async def _post_process(self, query: AuthorSearchQuery, data: List[PubmedNativeData]) -> List[AuthorData]:
        def query_to_func(body_institution, body_author, body_topic):
            def query_to_term(query):
                def make_string_term(body_string, q_value, operator):
                    if operator == 'in':
                        return q_value.lower() in body_string.lower()
                    else:
                        return (
                                q_value.lower() in body_string.lower().split(' ')
                            ) or (
                                body_string.lower() in q_value.lower().split(' ')
                            )
                
                if query['tag'] == 'and':
                    fields = query['fields_']
                    return all([query_to_term(field) for field in fields])
                elif query['tag'] == 'or':
                    fields = query['fields_']
                    return any([query_to_term(field) for field in fields])
                #elif query['tag'] == 'topic':
                #    operator = query['operator']
                #    value = operator['value']
                #    return make_string_term(body_topic, value, operator)
                elif query['tag'] == 'author':
                    operator = query['operator']
                    value = operator['value']
                    return make_string_term(body_author, value, operator)
                elif query['tag'] == 'institution':
                    operator = query['operator']
                    value = operator['value']
                    return make_string_term(body_institution, value, operator)
                else:
                    raise ValueError('Unknown tag')

            return query_to_term

        def institution_matches(inst1, inst2):
            match_count = 0
            if inst1 is None or inst2 is None:
                if inst2 == inst1:
                    return True
                else:
                    return False
            for part in inst1:

                if part[1] == 'postcode':
                    #Extract postcodes from other half
                    postcodes2 = [i[0] for i in inst2 if i[1] == 'postcode']
                    #If other half has a postcode, it must match
                    if len(postcodes2)>0:
                        if part[0] in postcodes2:
                            return True
                        else:
                            return False
                if part[1] == 'house':
                    #Extract houses from other half
                    houses2 = [i[0] for i in inst2 if i[1] == 'house']
                    #If other half has a house, it must match
                    if len(houses2)>0:
                        for house2 in houses2:
                            if part[0] in house2 or house2 in part[0]:
                                return True
                            else:
                                return False
                if part in inst2:
                    match_count += 1
            if match_count >= 4:
                return True
            else:
                return False

        def authors_match(author1, author2):
            proc_institution1 = author1.dict()['__root__']['proc_institution']
            proc_institution2 = author2.dict()['__root__']['proc_institution']
            if author1 == author2:
                return True
            elif institution_matches(proc_institution1, proc_institution2):
                return True
            else:
                return False
        def group_by_location(filtered_authors):
            final_list = []
            for i in filtered_authors:
                match_authors = []
                for j in filtered_authors:

                    if authors_match(i,j) and j not in match_authors:
                        match_authors.append(j)
                if match_authors not in final_list:
                    final_list.append(match_authors)
            
            return final_list
        
        def pick_largest_from_group(location_groups):
            finals = []
            for location_group in location_groups:
                lens = [len(str(i)) for i in location_group]
                group_index = lens.index(max(lens))
                location = location_group[group_index]
                if location not in finals:
                    finals.append(location)
            return finals
        
        coroutines = []
        for i in data:
            coroutines.append(process_paper_institutions(i))
        
        results = await gather(*coroutines)

        combined_authors = []
        for result in results:
            combined_authors += result.author_list

        query_dict = query.dict()['query']

        filtered_authors = []
        for i in combined_authors:
            author = i.__root__
            institution = author.institution
            if isinstance(author, ProcessedIndividual):
                last_name = author.last_name
                fore_name = author.fore_name
                last_is_present = query_to_func(institution, last_name, None)(query_dict)
                fore_is_present = query_to_func(institution, fore_name, None)(query_dict)
                is_present = fore_is_present and last_is_present
            else:
                collective_name = author.collective_name
                is_present = query_to_func(institution, collective_name, None)(query_dict)
            if is_present and i not in filtered_authors:
                filtered_authors.append(i)

        location_groups = group_by_location(filtered_authors)
        finals = pick_largest_from_group(location_groups)

        processed_author_data = []
        for author1 in finals:
            associated_with_author = []
            for paper in results:
                author_list = paper.author_list
                paper_dict = paper.dict()
                for author2 in author_list:
                    if authors_match(author1, author2) and paper_dict not in associated_with_author:
                        associated_with_author.append(paper_dict)
            paper_count = len(associated_with_author)
            processed_author_data.append(
                ProcessedAuthorData.parse_obj(
                    {
                        'author': author1.dict()['__root__'],
                        'papers': associated_with_author,
                        'paper_count': paper_count
                    }
                )
            )

        new_data = []
        for i in processed_author_data:
            data_dict = i.dict()
            author_info = data_dict['author']
            paper_count = data_dict['paper_count']
            paper_ids = []
            for i in data_dict['papers']:
                paper_id = i['paper_id']
                doi = paper_id['doi']
                pubmed_id = paper_id['pubmed']
                paper_ids.append(
                    {
                        'doi': doi,
                        'pubmed_id': pubmed_id
                    }
                )
            new_data.append(AuthorData.parse_obj({
                'preferred_name': {
                    'surname': author_info['last_name'],
                    'given_names': author_info['fore_name'],
                    'initials': author_info['initials']
                },
                'institution_current': {
                    'name': author_info['institution'],
                    'processed': author_info['proc_institution']
                },
                'paper_count': paper_count,
                'paper_ids': paper_ids
            }))
        return new_data



class PubmedBackend(Backend):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(max_requests_per_second = 9)
    
    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            api_key = self.api_key, 
            rate_limiter=self.rate_limiter
        )

    def author_search_engine(self) -> AuthorSearchQueryEngine:
        raise NotImplementedError

    def institution_search_engine(self) -> None:
        raise NotImplementedError
