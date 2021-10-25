from asyncio import gather, get_running_loop
from copy import copy
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
from matchmaker.query_engine.data_types import AuthorData, PaperData
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
from pydantic import BaseModel, Field
from matchmaker.query_engine.backends.tools import (
    replace_ids,
    replace_dict_tags,
)

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
    new_query_dict = query.dict()['__root__']
    new_query_dict = replace_dict_tags(
        new_query_dict,
        elocationid = 'doi'
    )
    return PubmedESearchQuery.parse_obj(new_query_dict)
def author_query_to_esearch(query: AuthorSearchQuery):
    # TODO convert topic to elocation
    # convert id.pubmed to pmid
    # convert id.doi to elocation
    return PubmedESearchQuery.parse_obj(query.dict()['__root__'])

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
        BasePaperSearchQueryEngine[List[PubmedNativeData], List[ProcessedData]]):
    api_key:str
    def __init__(self, api_key, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        self.api_key = api_key
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

    async def _post_process(self, query: PaperSearchQuery, data: List[PubmedNativeData]) -> List[ProcessedData]:
        results = []
        for i in data:
            results.append(await process_paper_institutions(i))

        return results


    async def _data_from_processed(self, data: List[ProcessedData]) -> List[PaperData]:
        def convert_data_dict(data_dict):
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

            author_list = data_dict['author_list']
            author_list_proc = []
            for author in author_list:
                if 'last_name' in author:
                    preferred_name = {
                        'surname': author['last_name'],
                        'given_names': author['fore_name'],
                        'initials': author['initials']
                    }
                else:
                    preferred_name = {
                        'surname': author['collective_name']
                    }
                #Institution details
                institution_current = {
                    'name': author['institution'],
                    'processed': author['proc_institution']
                }
                author_proc = {
                    'preferred_name': preferred_name,
                    'institution_current': institution_current
                }
                author_list_proc.append(author_proc)

            doi = data_dict['paper_id']['doi']
            pubmed = data_dict['paper_id']['pubmed']

            paper_id = {
                'doi': doi,
                'pubmed_id': pubmed
            }
            title = data_dict['title']
            year = data_dict['year']
            topics = data_dict['topics']
            source_title = data_dict['journal_title']
            source_title_abr = data_dict['journal_title_abr']
            keywords = data_dict['keywords']
            new_references = []
            if 'references' in data_dict and data_dict['references'] is not None:
                for reference in data_dict['references']:
                    new_references += [convert_data_dict(reference)]
            new_cited_bys = []
            if 'cited_by' in data_dict and data_dict['cited_by'] is not None:
                for cited_by in data_dict['cited_by']:
                    new_cited_bys += [convert_data_dict(cited_by)]
            return {
                'paper_id': paper_id,
                'title': title,
                'authors': author_list_proc,
                'year': year,
                'source_title': source_title,
                'source_title_abr': source_title_abr,
                'abstract': abstract_proc,
                'keywords': keywords,
                'topics': topics,
                'references': new_references,
                'cited_by': new_cited_bys
            }
        

        new_data = []
        for i in data:
            data_dict = i.dict()
            new_data_dict = convert_data_dict(data_dict)
            new_data.append(PaperData.parse_obj(new_data_dict))
            
        return new_data
        #return [paper_from_native(datum) for datum in data]

class AuthorSearchQueryEngine(
        BaseAuthorSearchQueryEngine[List[PubmedNativeData], List[ProcessedAuthorData]]):
        
    def __init__(self, api_key, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        self.api_key = api_key
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
            output = await esearch_on_query(query, client, api_key=self.api_key)
            id_list = output.pubmed_id_list
            output = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = id_list), client, api_key = self.api_key)

            native = [PubmedNativeData.parse_obj(i.dict()) for i in output]
            return native
        metadata = {
            'efetch': 1,
            'esearch': 1
        }
        return make_coroutine, metadata


    async def _post_process(self, query: PaperSearchQuery, data: List[PubmedNativeData]) -> List[ProcessedAuthorData]:
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
            set_list = []
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

        authors = [i.author_list for i in results]
        combined_authors = []
        for result in results:
            combined_authors += result.author_list

        query_dict = query.dict()['__root__']

        filtered_authors = []
        for i in combined_authors:
            author = i.__root__
            institution = author.institution
            proc_institution = author.proc_institution
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

        return processed_author_data

    async def _data_from_processed(self, data: List[ProcessedAuthorData]) -> List[AuthorData]:

        new_data = []
        for i in data:
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
        return AuthorSearchQueryEngine(
            api_key = self.api_key, 
            rate_limiter=self.rate_limiter
        )

    def institution_search_engine(self) -> None:
        raise NotImplementedError