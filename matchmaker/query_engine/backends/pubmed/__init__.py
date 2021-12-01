from asyncio import gather, get_running_loop
from copy import copy, deepcopy
from dataclasses import replace
from pprint import pprint
from typing import Annotated, Awaitable, Callable, Dict, List, Tuple, TypeVar, Union, Optional, Any

from aiohttp import ClientSession
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.backends import MetadataType, ProcessDataIter
from matchmaker.query_engine.backends.web import (
    WebAuthorSearchQueryEngine,
    WebPaperSearchQueryEngine,
    NewAsyncClient,
    RateLimiter,
    WebNativeQuery
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
from matchmaker.query_engine.backends.tools import replace_dict_tags
from matchmaker.query_engine.types.data import AuthorData, PaperData
from matchmaker.query_engine.types.query import AuthorSearchQuery, PaperSearchQuery
from matchmaker.query_engine.types.query import (
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
from matchmaker.query_engine.types.selector import (
    PaperDataAllSelected,
    PaperDataSelector,
    SubPaperDataAllSelected,
    SubPaperDataSelector,
    AuthorDataSelector
)
from pydantic import BaseModel, Field
from pydantic.error_wrappers import ValidationError
from matchmaker.query_engine.backends.tools import execute_callback_on_tag
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


def convert_paper_id(dict_structure):
    operator = dict_structure['operator']
    assert dict_structure['tag'] == 'id'
    operator_value = operator['value']
    id_searches = []
    for id_type, value in operator_value.items():
        if 'doi' == id_type and value is not None:
            id_searches.append({
                'tag': 'elocationid',
                'operator': {
                    'tag': operator['tag'],
                    'value': value
                }
            })
        elif 'pubmed_id' == id_type and value is not None:
            id_searches.append({
                'tag': 'pmid',
                'operator': {
                    'tag': operator['tag'],
                    'value': value
                }
            })
        elif 'scopus_id' == id_type and value is not None:
            raise ValueError('Scopus id queries not supported')
        elif value is None:
            pass
        else:
            raise ValueError(f'Unknown id type: {id_type}')
    if len(id_searches) == 0:
        raise ValueError('No ids selected')
    elif len(id_searches) ==1:
        return id_searches[0]
    else:
        return {
            'tag': 'or',
            'fields_': id_searches
        }

def paper_query_to_esearch(query: PaperSearchQuery):
    # TODO convert topic to elocation
    # convert id.pubmed to pmid
    # convert id.doi to elocation
    
    #new_query_dict = replace_ids(query.dict()['__root__'])
    new_query_dict = query.dict()['query']
    new_query_dict = replace_dict_tags(
        new_query_dict
    )
    new_query_dict = execute_callback_on_tag(new_query_dict, 'id', convert_paper_id)
    return PubmedESearchQuery.parse_obj(new_query_dict)

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


DataForProcess = TypeVar('DataForProcess')
ProcessedDataNew = TypeVar('ProcessedDataNew')
class PubmedProcessedData(ProcessDataIter[DataForProcess, ProcessedDataNew]):
    pass

class PaperSearchQueryEngine(
    WebPaperSearchQueryEngine[
        WebNativeQuery[List[PubmedNativeData]],
        List[PubmedNativeData], 
        PubmedProcessedData[PubmedNativeData, PaperData]
    ]
):
    api_key:str
    def __init__(self, api_key: str, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        self.api_key = api_key
        esearch_field_bools = {'paper_id':{'pubmed_id':True}}
        efetch_field_bools = {
            'paper_id': {
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
        self.esearch_fields = PaperDataSelector.parse_obj(esearch_field_bools)
        self.efetch_fields = PaperDataSelector.parse_obj(efetch_field_bools)
        self.elink_refs_fields = PaperDataSelector.parse_obj({
            'references': esearch_field_bools
        })
        self.elink_refs_details_fields = PaperDataSelector.parse_obj({
            'references': efetch_field_bools
        })
        self.elink_citeds_fields = PaperDataSelector.parse_obj({
            'cited_by': esearch_field_bools
        })
        self.elink_citeds_details_fields = PaperDataSelector.parse_obj({
            'cited_by': efetch_field_bools
        })

        self.possible_searches = [
            self.esearch_fields,
            self.efetch_fields,
            self.elink_refs_fields,
            self.elink_citeds_fields
        ]
        self.available_fields = PaperDataSelector.parse_obj({
            'paper_id': {
                'doi': True,
                'pubmed_id':True
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
            'topics': True,
            'references': efetch_field_bools,
            'cited_by': efetch_field_bools
        })
        super().__init__(rate_limiter, *args, **kwargs)

    async def _query_to_awaitable(self, query: PaperSearchQuery, client: NewAsyncClient) -> Tuple[
        Callable[
            [NewAsyncClient], 
            Awaitable[List[PubmedNativeData]]
        ], 
        Callable[[], Awaitable[Dict[str, Tuple[int, Optional[int]]]]]
    ]:
        if query.selector in self.available_fields:
            pass
        else:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        
        async def get_metadata() -> MetadataType:
            def tuple_set_attr(old_tuple: Tuple[int,...], index: int, new_value) -> Tuple[int,...]:
                if not index < len(old_tuple):
                    raise ValueError(f'{index} not in {old_tuple}')
                tuple_list = list(old_tuple)
                tuple_list[index] = new_value
                return tuple(tuple_list)
            metadata = {
                'esearch': (1, None),
                'efetch': (0, None),
                'elink': (0, None)
            }
            if query.selector.any_of_fields(self.efetch_fields):
                metadata['efetch'] = tuple_set_attr(metadata['efetch'], 0, metadata['efetch'][0] + 1)
            
            if query.selector.any_of_fields(self.elink_refs_fields) or query.selector.any_of_fields(self.elink_refs_details_fields):
                metadata['elink'] = tuple_set_attr(metadata['elink'], 0, metadata['elink'][0] + 1)
                if query.selector.any_of_fields(self.elink_refs_details_fields):
                    metadata['efetch'] = tuple_set_attr(metadata['efetch'], 0, metadata['efetch'][0] + 1)
            
            if query.selector.any_of_fields(self.elink_citeds_fields) or query.selector.any_of_fields(self.elink_citeds_details_fields):
                metadata['elink'] = tuple_set_attr(metadata['elink'], 0, metadata['elink'][0] + 1)
                if query.selector.any_of_fields(self.elink_citeds_details_fields):
                    metadata['efetch'] = tuple_set_attr(metadata['efetch'], 0, metadata['efetch'][0] + 1)
            return metadata
        
        pubmed_search_query = paper_query_to_esearch(query)

        async def get_data(client: ClientSession) -> List[PubmedNativeData]:
            async def id_mapper_to_unique_list(id_mapper: Dict[str, Optional[List[str]]]) -> List[str]:
                unique_ids = []
                for linked_ids in id_mapper.values():
                    if linked_ids is not None:
                        for linked_id in linked_ids:
                            if linked_id not in unique_ids:
                                unique_ids.append(linked_id)
                return unique_ids
            async def get_papers_from_index(
                id_mapper: Dict[str, Optional[List[str]]], 
                sub_paper_index: Dict[str, PubmedEFetchData]
            ) -> Dict[str, List[PubmedEFetchData]]:
                id_mapper_papers = {}
                for search_id, id_list in id_mapper.items():
                    if id_list is not None:
                        id_mapper_papers[search_id] = [sub_paper_index[sub_id] for sub_id in id_list]
                    else:
                        id_mapper_papers[search_id] = []
                return id_mapper_papers


            """
            If you asked for anything: esearch
            If you asked for fetch field: efetch
            If you asked for refs doi or details: elink(refs)
                if refs details: efetch(refs)
            If you asked for citeds doi or details: elink(cited)
                if citeds details: efetch(citeds)
            """

            search_result = await esearch_on_query(pubmed_search_query, client, api_key=self.api_key)
            if query.selector.any_of_fields(self.efetch_fields):
                fetch_result_raw = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = search_result.pubmed_id_list), client, api_key=self.api_key)
                fetch_result = {i.paper_id.pubmed: i for i in fetch_result_raw}
            else:
                fetch_result = None
            if query.selector.any_of_fields(self.elink_refs_fields) or query.selector.any_of_fields(self.elink_refs_details_fields):
                link_result_refs_raw = await elink_on_id_list(
                    PubmedELinkQuery(
                        pubmed_id_list = search_result.pubmed_id_list, 
                        linkname = 'pubmed_pubmed_refs'
                    ),
                    client, 
                    api_key=self.api_key
                )
                link_result_refs = link_result_refs_raw.id_mapper
                if query.selector.any_of_fields(self.elink_refs_details_fields):
                    ref_unique_fetch_list = await id_mapper_to_unique_list(link_result_refs)
                    fetch_result_refs_raw = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = ref_unique_fetch_list), client, api_key=self.api_key)
                    sub_paper_index_refs = {i.paper_id.pubmed: i for i in fetch_result_refs_raw}
                    fetch_result_refs = await get_papers_from_index(link_result_refs, sub_paper_index_refs)
                else:
                    fetch_result_refs = None
            
            else:
                link_result_refs = None
                fetch_result_refs = None


            if query.selector.any_of_fields(self.elink_citeds_fields) or query.selector.any_of_fields(self.elink_citeds_details_fields):
                link_result_citeds_raw = await elink_on_id_list(
                    PubmedELinkQuery(
                        pubmed_id_list = search_result.pubmed_id_list, 
                        linkname = 'pubmed_pubmed_citedin'
                    ),
                    client, 
                    api_key=self.api_key
                )
                link_result_citeds = link_result_citeds_raw.id_mapper
                if query.selector.any_of_fields(self.elink_citeds_details_fields):
                    cited_by_unique_fetch_list = await id_mapper_to_unique_list(link_result_citeds)
                    fetch_result_citeds_raw = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = cited_by_unique_fetch_list), client, api_key=self.api_key)
                    sub_paper_index_cited = {i.paper_id.pubmed: i for i in fetch_result_citeds_raw}
                    fetch_result_citeds = await get_papers_from_index(link_result_citeds, sub_paper_index_cited)
                else:
                    fetch_result_citeds = None
            else:
                link_result_citeds = None
                fetch_result_citeds = None


            native_papers = []
            for pubmed_id in search_result.pubmed_id_list:
                native_data_dict: Dict[str, Any]
                if fetch_result is None:
                    native_data_dict = {'paper_id': {'pubmed': pubmed_id}}
                else:
                    native_data_dict = fetch_result[pubmed_id].dict()
                
                if link_result_citeds is not None:
                    if fetch_result_citeds is None:
                        references = []
                        relevant_citeds = link_result_citeds[pubmed_id]
                        if relevant_citeds is not None:
                            for i in relevant_citeds:
                                references.append({'paper_id': {'pubmed': i}})
                            native_data_dict['references'] = references
                    else:
                        references = []
                        relevant_citeds = fetch_result_citeds[pubmed_id]
                        for i in relevant_citeds:
                            native_data_dict['references'] = i.dict()
                    native_data_dict['references'] = references

                if link_result_refs is not None:
                    if fetch_result_refs is None:
                        references = []
                        relevant_refs = link_result_refs[pubmed_id]
                        if relevant_refs is not None:
                            for i in relevant_refs:
                                references.append({'paper_id': {'pubmed': i}})
                            native_data_dict['references'] = references
                    else:
                        references = []
                        relevant_refs = fetch_result_refs[pubmed_id]
                        for i in relevant_refs:
                            native_data_dict['references'] = i.dict()
                    native_data_dict['references'] = references

                native_paper = PubmedNativeData.parse_obj(native_data_dict)
                native_papers.append(native_paper)

            return native_papers

        return get_data, get_metadata

    async def _post_process(self, query: PaperSearchQuery, data: List[PubmedNativeData]) -> PubmedProcessedData[PubmedNativeData, PaperData]:
        def process_sub_paper_data(data_dict, selector: SubPaperDataSelector):
            new_data_dict = {}

            if selector.any_of_fields(SubPaperDataSelector.parse_obj(
                {'paper_id':{
                    'doi': True,
                    'pubmed_id':True
                }}
            )):
                paper_id = {}
                if SubPaperDataSelector.parse_obj({'paper_id':{'doi':True}}) in selector:
                    paper_id['doi'] = data_dict['paper_id']['doi']
                if SubPaperDataSelector.parse_obj({'paper_id':{'pubmed_id':True}}) in selector:
                    paper_id['pubmed_id'] = data_dict['paper_id']['pubmed']

                new_data_dict['paper_id'] = paper_id


            if SubPaperDataSelector(title = True) in selector:
                new_data_dict['title'] = data_dict['title']

            if SubPaperDataSelector(year = True) in selector:
                new_data_dict['year'] = data_dict['year']


            if selector.any_of_fields(
                SubPaperDataSelector.parse_obj({
                    'authors':{
                        'preferred_name':{
                            'given_names': True,
                            'surname': True,
                            'initials': True
                        },
                        'institution_current':{
                            'name': True,
                            'processed': True
                        }
                    }
                })
            ):
                new_authors = []
                for author in data_dict['author_list']:
                    author_root = author
                    new_author = {}
                    if selector.any_of_fields(SubPaperDataSelector.parse_obj({
                        'authors':{
                            'preferred_name':{
                                'surname': True,
                                'given_names': True,
                                'initials': True
                            }
                        }
                    })):
                        new_name = {}
                        if SubPaperDataSelector.parse_obj({
                            'authors':{
                                'preferred_name':{
                                    'surname': True
                                }
                            }
                        }) in selector:
                            if 'last_name' in author_root:
                                new_name['surname'] = author_root['last_name']
                            else:
                                new_name['surname'] = author_root['collective_name']
                        if SubPaperDataSelector.parse_obj({
                            'authors':{
                                'preferred_name':{
                                    'given_names': True
                                }
                            }
                        }) in selector:
                            if 'given_names' in author_root:
                                new_name['given_names'] = author_root['fore_name']
                            else:
                                new_name['given_names'] = None
                        if SubPaperDataSelector.parse_obj({
                            'authors':{
                                'preferred_name':{
                                    'initials': True
                                }
                            }
                        }) in selector:
                            if 'initials' in author_root:
                                new_name['initials'] = author_root['initials']
                        new_author['preferred_name'] = new_name
                    
                    if selector.any_of_fields(SubPaperDataSelector.parse_obj({
                            'authors':{
                                'institution_current':{
                                    'name': True,
                                    'processed': True
                                }
                            }
                    })):
                        new_institution = {}
                        institution = author_root['institution']
                        if SubPaperDataSelector.parse_obj({
                            'authors':{
                                'institution_current':{
                                    'name': True
                                }
                            }
                        }) in selector:
                            new_institution['name'] = institution
                        if SubPaperDataSelector.parse_obj({
                            'authors':{
                                'institution_current':{
                                    'processed': True
                                }
                            }
                        }) in selector:
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
        model = PaperData.generate_model_from_selector(selector)
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

        async def process_paper_data(data: PubmedNativeData) -> PaperData:
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


        data_iter = iter(data)
        return PubmedProcessedData[PubmedNativeData, PaperData](data_iter, process_paper_data)





"""
class AuthorSearchQueryEngine(
        WebAuthorSearchQueryEngine[List[PubmedNativeData]]):
        
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
"""


class PubmedBackend(Backend):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(max_requests_per_second = 9)
    
    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            api_key = self.api_key, 
            rate_limiter=self.rate_limiter
        )

    def author_search_engine(self) -> None:
        raise NotImplementedError

    def institution_search_engine(self) -> None:
        raise NotImplementedError
