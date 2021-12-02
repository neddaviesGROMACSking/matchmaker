from matchmaker.matching_engine import StackedAuthorMatrix
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend, paper_query_to_scopus
from matchmaker.query_engine.backends.scopus import PaperSearchQueryEngine as ScopusPaperSearchQueryEngine
from matchmaker.query_engine.backends.scopus import AuthorSearchQueryEngine as ScopusAuthorSearchQueryEngine
from matchmaker.query_engine.backends.scopus import InstitutionSearchQueryEngine as ScopusInstitutionSearchQueryEngine

from matchmaker.query_engine.types.data import AuthorData, PaperData, InstitutionData
from matchmaker.query_engine.types.query import AuthorSearchQuery, PaperSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.types.selector import AuthorDataAllSelected, InstitutionDataSelector, PaperDataSelector, PaperDataAllSelected, AuthorDataSelector
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend
from typing import AsyncIterator, Iterator, Optional, Tuple, Callable, Awaitable, Dict, List, Generic, TypeVar, Union, Any
from asyncio import get_running_loop, gather
from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError, SearchNotPossible
from dataclasses import dataclass
import pdb
from pybliometrics.scopus.utils.constants import SEARCH_MAX_ENTRIES
#from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError
from matchmaker.query_engine.backends.tools import TagNotFound, execute_callback_on_tag
from pybliometrics.scopus.exception import ScopusQueryError
from copy import deepcopy
from matchmaker.query_engine.backends.metas import MetaNativeQuery, MetaPaperSearchQueryEngine, MetaAuthorSearchQueryEngine
from matchmaker.query_engine.backends import AsyncProcessDataIter, MetadataType
from enum import Enum
from functools import reduce
DictStructure = Dict[str, Union[str, 'ListStructure', 'DictStructure']]
ListStructure = List[Union[str, 'ListStructure', 'DictStructure']]



def bin_items(items: List[str], bin_limit: int) -> List[List[str]]:
    binned_items = []
    current_bin_index = 0
    for i in items:
        if current_bin_index >= len(binned_items):
            binned_items.append([])
        binned_items[current_bin_index].append(i)
        if len(binned_items[current_bin_index]) >= bin_limit:
            current_bin_index += 1
    return binned_items



async def get_doi_list_from_data(papers: List[PaperData]) -> List[str]:
    return [paper.paper_id.doi for paper in papers if paper.paper_id.doi is not None]

async def get_doi_query_from_list(dois: List[str], selector) -> PaperSearchQuery:
    query = {
        'query':{
            'tag': 'or',
            'fields_': [
                {
                    'tag': 'id',
                    'operator': {
                        'tag': 'equal',
                        'value': {'doi': i}
                    }
                } for i in dois
            ]
        },
        'selector': selector.dict()
    }
    return PaperSearchQuery.parse_obj(query)

async def get_dois_remaining(scopus_dois: List[str], pubmed_dois: List[str]) -> List[str]:
    return [doi for doi in scopus_dois if doi not in pubmed_dois]

DataForProcess = TypeVar('DataForProcess')
ProcessedData = TypeVar('ProcessedData')
class ProcessedMeta(AsyncProcessDataIter[DataForProcess, ProcessedData]):
    pass


class CombinedIterator(AsyncIterator):
    def __init__(self, async_iterators: List[AsyncIterator] = [], sync_iterators: List[Iterator] = []) -> None:
        self._async_iterators = async_iterators
        self._sync_iterators = sync_iterators
    def __aiter__(self):
        return self
    async def __anext__(self):
        for i in self._async_iterators:
            try:
                return i.__anext__()
            except StopAsyncIteration:
                pass
        for i in self._sync_iterators:
            try:
                return i.__next__()
            except StopIteration:
                pass
        raise StopAsyncIteration



class PaperSearchQueryEngine(
    MetaPaperSearchQueryEngine[
        MetaNativeQuery[AsyncIterator[PaperData]],
        AsyncIterator[PaperData], 
        ProcessedMeta[PaperData, PaperData]
    ]
):
    def __init__(
        self, 
        scopus_paper_search,
        pubmed_paper_search,
        complete_search_request_limit: int = 100
    ) -> None:
        self.scopus_paper_search = scopus_paper_search
        self.pubmed_paper_search = pubmed_paper_search
        self.complete_search_request_limit = complete_search_request_limit
        self.pubmed_scopus_intercept_selector = PaperDataSelector.generate_subset_selector(self.scopus_paper_search.available_fields, self.pubmed_paper_search.available_fields)
        self.available_fields = PaperDataAllSelected
        self.doi_selector = PaperDataSelector.parse_obj({'paper_id':{'doi': True}})
        self.possible_searches = [
            self.doi_selector,
            self.pubmed_scopus_intercept_selector,
            self.scopus_paper_search.available_fields,
            self.pubmed_paper_search.available_fields
        ]
    
    async def _query_to_awaitable(self, query: PaperSearchQuery) -> Tuple[Callable[[], Awaitable[AsyncIterator[PaperData]]], Callable[[], Awaitable[MetadataType]]]:
        if query.selector not in self.available_fields:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)


        scopus_standard_fields = self.scopus_paper_search.possible_searches[1]
        scopus_complete_fields = self.scopus_paper_search.possible_searches[0]
        pubmed_fields = self.pubmed_paper_search.available_fields

        class Strategy(Enum):
            ScopusStandard = 'ScopusStandard'
            ScopusStandardThenPubmed = 'ScopusStandardThenPubmed'
            ScopusStandardThenPubmedThenScopusComplete = 'ScopusStandardThenPubmedThenScopusComplete'
            ScopusComplete = 'ScopusComplete'
            ScopusCompleteThenPubmed = 'ScopusCompleteThenPubmed'
        
        not_scopus_standard_fields = PaperDataSelector.inverted(scopus_standard_fields)
        exclusive_complete_fields = scopus_complete_fields | not_scopus_standard_fields
        not_exclusive_complete_fields = PaperDataSelector.inverted(exclusive_complete_fields)
        if query.selector in scopus_standard_fields:
            strategy = Strategy.ScopusStandard
        elif query.selector in ((scopus_standard_fields | pubmed_fields) & not_exclusive_complete_fields):
            strategy = Strategy.ScopusStandardThenPubmed
        elif query.selector in (scopus_standard_fields | pubmed_fields):
            strategy = Strategy.ScopusStandardThenPubmedThenScopusComplete
        elif query.selector in scopus_complete_fields:
            strategy = Strategy.ScopusComplete
        elif query.selector in (scopus_complete_fields | pubmed_fields):
            strategy = Strategy.ScopusCompleteThenPubmed
        else:
            raise ValueError('Fields set as available but no strategy supported')

        all_ids_selector = PaperDataSelector.parse_obj({'paper_id': True})
        if (
            strategy == Strategy.ScopusCompleteThenPubmed 
            or strategy == Strategy.ScopusStandardThenPubmed
            or strategy == Strategy.ScopusStandardThenPubmedThenScopusComplete
        ):
            pubmed_selector = (all_ids_selector | query.selector) & self.pubmed_paper_search.available_fields
        if (
            strategy == Strategy.ScopusStandardThenPubmed
            or strategy == Strategy.ScopusStandardThenPubmedThenScopusComplete
        ):
            scopus_standard_selector = (all_ids_selector | query.selector) & scopus_standard_fields
            standard_query = deepcopy(query)
            standard_query.selector = scopus_standard_selector
        if strategy == Strategy.ScopusCompleteThenPubmed or strategy == Strategy.ScopusStandardThenPubmedThenScopusComplete:
            scopus_complete_selector = (all_ids_selector | query.selector) & scopus_complete_fields
            complete_query = deepcopy(query)
            complete_query.selector = scopus_complete_selector

        async def get_metadata() -> MetadataType:
            if strategy == 'ScopusStandard' or strategy == 'ScopusComplete':
                data_iter = await self.scopus_paper_search(query)
                metadata = await data_iter.metadata()
                return metadata
            elif strategy == 'ScopusCompleteThenPubmed' or strategy == 'ScopusStandardThenPubmed':
                scopus_data_iter = await self.scopus_paper_search(complete_query)
                scopus_metadata = await scopus_data_iter.metadata()
                # Invarient - pubmed requests are independent of query, only dependent on selector
                """
                # TODO : Try generic form
                fake_pubmed_query = PaperSearchQuery.parse_obj({
                    'query': {},
                    'selector': pubmed_selector
                })
                """
                fake_pubmed_query = PaperSearchQuery.parse_obj({
                    'query': {
                        'tag': 'author',
                        'operator': {
                            'tag': 'equal',
                            'value': 'John Smith'
                        }
                    },
                    'selector': pubmed_selector
                })
                pubmed_data_iter = await self.pubmed_paper_search(fake_pubmed_query)
                pubmed_metadata = await pubmed_data_iter.metadata()
                new_requests = {**scopus_metadata.requests, **pubmed_metadata.requests}
                metadata = MetadataType.parse_obj({
                    'requests': new_requests,
                    'no_results': scopus_metadata.no_results
                })
                return metadata
            elif strategy == 'ScopusStandardThenPubmedThenScopusComplete':
                scopus_data_iter_standard = await self.scopus_paper_search(complete_query)
                scopus_metadata_standard = await scopus_data_iter_standard.metadata()

                scopus_data_iter_complete = await self.scopus_paper_search(complete_query)
                scopus_metadata_complete = await scopus_data_iter_complete.metadata()

                min_scopus_requests: int = scopus_metadata_standard.requests['scopus_search'].requests_required
                max_scopus_requests: int = scopus_metadata_standard.requests['scopus_search'].requests_required + scopus_metadata_complete.requests['scopus_search'].requests_required
                
                new_scopus_requests_dict = {
                    'scopus_search': {
                        'requests_required': {
                            'lower_bound': min_scopus_requests,
                            'upper_bound': max_scopus_requests
                        },
                        'requests_remaining': scopus_metadata_complete.requests['scopus_search'].requests_remaining
                    }
                }
                # Invarient - pubmed requests are independent of query, only dependent on selector
                """
                # TODO : Try generic form
                fake_pubmed_query = PaperSearchQuery.parse_obj({
                    'query': {},
                    'selector': pubmed_selector
                })
                """
                fake_pubmed_query = PaperSearchQuery.parse_obj({
                    'query': {
                        'tag': 'author',
                        'operator': {
                            'tag': 'equal',
                            'value': 'John Smith'
                        }
                    },
                    'selector': pubmed_selector
                })
                pubmed_data_iter = await self.pubmed_paper_search(fake_pubmed_query)
                pubmed_metadata = await pubmed_data_iter.metadata()
                metadata = MetadataType.parse_obj({
                    'requests': {
                        **new_scopus_requests_dict,
                        **pubmed_metadata.requests
                    }
                })
                return metadata
            else:
                raise ValueError('Unknown strategy')


        async def get_data() -> AsyncIterator:
            """
            If you select just dois, standard query is all you get
            If you select fields from pubmed intercept scopus, you get pubmed results and maybe go back to scopus for more data
            If you select fields from pubmed you get just pubmed results
            If you select fields from scopus you get just scopus results
            """
            if strategy == Strategy.ScopusStandard or strategy == Strategy.ScopusComplete:
                return await self.scopus_paper_search(query)
            elif strategy == Strategy.ScopusCompleteThenPubmed:
                # Step 1 - get complete results
                scopus_complete_data_async_iter = await self.scopus_paper_search(complete_query)
                # Step 2 - get pubmed results for these ids
                scopus_complete_data = [i async for i in scopus_complete_data_async_iter]
                scopus_complete_data_iter = iter(scopus_complete_data)
                doi_list_scopus = await get_doi_list_from_data(scopus_complete_data)
                doi_query_pubmed = await get_doi_query_from_list(doi_list_scopus, pubmed_selector)
                pubmed_data_iter = await self.pubmed_paper_search(doi_query_pubmed)
                return CombinedIterator([pubmed_data_iter], [scopus_complete_data_iter])
            elif strategy == Strategy.ScopusStandardThenPubmed:
                # Step 1 - get standard results
                scopus_standard_data_async_iter = await self.scopus_paper_search(standard_query)
                # Step 2 - get pubmed results for these ids
                scopus_standard_data = [i async for i in scopus_standard_data_async_iter]
                scopus_standard_data_iter = iter(scopus_standard_data)
                doi_list_scopus = await get_doi_list_from_data(scopus_standard_data)
                doi_query_pubmed = await get_doi_query_from_list(doi_list_scopus, pubmed_selector)
                pubmed_data_iter = await self.pubmed_paper_search(doi_query_pubmed)
                return CombinedIterator([pubmed_data_iter], [scopus_standard_data_iter])
            elif strategy == Strategy.ScopusStandardThenPubmedThenScopusComplete:
                # Step 1 - get standard results
                scopus_standard_data_async_iter = await self.scopus_paper_search(standard_query)
                # Step 2 - get pubmed results for these ids
                scopus_standard_data = [i async for i in scopus_standard_data_async_iter]
                scopus_standard_data_iter = iter(scopus_standard_data)
                doi_list_scopus = await get_doi_list_from_data(scopus_standard_data)
                doi_query_pubmed = await get_doi_query_from_list(doi_list_scopus, pubmed_selector)
                pubmed_data_async_iter = await self.pubmed_paper_search(doi_query_pubmed)
                pubmed_data = [i async for i in pubmed_data_async_iter]
                pubmed_data_iter = iter(pubmed_data)
                doi_list_pubmed = await get_doi_list_from_data(pubmed_data)
                dois_remaining = await get_dois_remaining(doi_list_scopus, doi_list_pubmed)
                complete_no_requests = len(dois_remaining)//25 +2
                
                # Step 3 - get estimate for returning to scopus for more info
                #pubmed will do same as always number of requests!
                #But nature of the query depends upon the results of standard_native_data

                if self.complete_search_request_limit < complete_no_requests:
                    return CombinedIterator(
                        sync_iterators=[
                            scopus_standard_data_iter, 
                            pubmed_data_iter
                        ]
                    )
                else:
                    #split doi list into blocks of 25 (25 per request),
                    # to reduce url length per length
                    
                    binned_dois = bin_items(dois_remaining, 25)
                    
                    async def get_paper_data_from_dois(dois):
                        doi_query_scopus = await get_doi_query_from_list(dois, complete_query.selector)
                        return await self.scopus_paper_search(doi_query_scopus)
                    
                    results = await gather(*list(map(get_paper_data_from_dois, binned_dois)))
                    
                    concat_results = []
                    for i in results:
                        total = [data async for data in i]
                        concat_results += total

                    results_iter = iter(concat_results)
                    
                    return CombinedIterator(
                        sync_iterators = [
                            scopus_standard_data_iter, 
                            pubmed_data_iter,
                            results_iter
                        ]
                    )
                    
            else:
                raise ValueError('Unknown strategy')

        return get_data, get_metadata

    async def _post_process(self, query: PaperSearchQuery, data: AsyncIterator) -> CombinedIterator:
        model = PaperData.generate_model_from_selector(query.selector)
        def merge_papers(papers: List[PaperData]) -> PaperData:
            def merge(paper1: PaperData, paper2: PaperData) -> PaperData:
                DictType = Dict[str, Union[Any, 'DictType']]
                def merge_lists(list1: List[Any], list2: List[Any]) -> List[Any]:
                    raise NotImplementedError
                    # TODO Produce list merging algorithm
                    #for item in list1:
                    #    if item is not None and 
                def merge_dicts(paper1_dict: DictType, paper2_dict: DictType):
                    merged_dict = {}
                    for k, v in paper1_dict.items():
                        if k in paper2_dict and paper2_dict[k] is not None:
                            competing_v = paper2_dict[k]
                            if v == competing_v:
                                merged_dict[k] = v
                            else:
                                if isinstance(v, dict):
                                    merged_dict[k] = merge_dicts(v, competing_v)
                                elif isinstance(v, list):
                                    if isinstance(competing_v, list):
                                        merged_dict[k] = merge_lists(v, competing_v)
                                    else:
                                        raise ValueError('List found in one paper but not in other')
                                else:
                                    len_v = len(str(v))
                                    len_comp_v = len(str(competing_v))
                                    if len_comp_v > len_v:
                                        merged_dict[k] = competing_v
                                    else:
                                        # Note: This does assume that for different strings of the same length
                                        # in the same paper, it doesn't matter which you choose
                                        merged_dict[k] = v
                        else:
                            merged_dict[k] = v
                    for k, v in paper2_dict.items():
                        if k not in merged_dict or (merged_dict[k] is None and v is not None):
                            merged_dict[k] = v
                    return merged_dict

                paper1_dict = paper1.dict()
                paper2_dict = paper2.dict()
                merged_dict = merge_dicts(paper1_dict, paper2_dict)
                return model.parse_obj(merged_dict)

            if len(papers) ==1:
                return model.parse_obj(papers[0].dict())
            else:
                return reduce(lambda x, y: merge(x,y), papers)

        new_data = []
        id_log = []
        raw_results = [i async for i in data]
        for i in raw_results:
            if i.paper_id not in id_log:
                matching_papers = [j for j in raw_results if j.paper_id == i.paper_id]
                if len(matching_papers) >= 1:
                    new_paper = merge_papers(matching_papers)
                else:
                    raise ValueError('Paper not found')
                id_log.append(new_paper.paper_id)
                new_data.append(new_paper)
        data_iter = iter(new_data)
        return CombinedIterator(sync_iterators= [data_iter])


class AuthorSearchQueryEngine(
        MetaAuthorSearchQueryEngine[
            MetaNativeQuery[AsyncIterator[AuthorData]],
            AsyncIterator[AuthorData], 
            ProcessedMeta[AuthorData, AuthorData]
        ]
    ):
    scopus_paper_search: ScopusPaperSearchQueryEngine
    scopus_author_search: ScopusAuthorSearchQueryEngine
    scopus_institution_search: ScopusInstitutionSearchQueryEngine
    def __init__(
        self,
        scopus_paper_search: ScopusPaperSearchQueryEngine,
        scopus_author_search: ScopusAuthorSearchQueryEngine,
        scopus_institution_search: ScopusInstitutionSearchQueryEngine
    ) -> None:
        self.max_entries = SEARCH_MAX_ENTRIES
        self.scopus_paper_search = scopus_paper_search
        self.scopus_author_search = scopus_author_search
        self.scopus_institution_search = scopus_institution_search
        self.available_fields = AuthorDataSelector.parse_obj({
            'id':{
                'scopus_id': True
            },
            'preferred_name':{
                'surname': True,
                'initials': True,
                'given_names': True,
            },
            'subjects': {
                'name': True,
                'paper_count': True
            },
            'institution_current': {
                'name': True,
                'id':{
                    'scopus_id': True
                },
                'processed': True
            },
            'other_institutions': {
                'id': {
                    'scopus_id': True
                }
            },
            'paper_count': True,
            'paper_ids': True
        })
        self.exclusive_author_fields = AuthorDataSelector.parse_obj({
                'preferred_name': {
                    'initials': True
                },
                'subjects': {
                    'name': True,
                    'paper_count': True
                },
                'institution_current': {
                    'name': True,
                    'id':{
                        'scopus_id': True
                    },
                    'processed': True
                }
            })
        self.paper_fields = AuthorDataSelector.parse_obj({
                'id':{
                    'scopus_id': True
                },
                'preferred_name': {
                    'surname': True,
                    'given_names': True
                },
                'other_institutions': {
                    'id':{
                        'scopus_id': True
                    }
                },
                'paper_count': True,
                'paper_ids': True
            })
        
        self.possible_searches = [
            #self.scopus_author_search.available_fields,
            #self.paper_and_institution_fields,
            AuthorDataSelector.parse_obj({
                'id':{
                    'scopus_id': True,
                    'pubmed_id': True
                },
                'preferred_name': {
                    'surname': True,
                    'initials': True,
                    'given_names': True
                },
                'subjects': {
                    'name': True,
                    'paper_count': True
                },
                'other_institutions': {
                    'id':{
                        'scopus_id': True,
                        'pubmed_id': True
                    },
                    'name': True,
                    'processed': True
                },
                'paper_count': True,
                'paper_ids': True
            }),
        ]


    async def _query_to_awaitable(self, query: AuthorSearchQuery) -> Tuple[Callable[[], Awaitable[List[AuthorData]]], Dict[str, int]]:
        """
        if one of the standard fields is asked for, 
        """
        if query.selector not in self.available_fields:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        
        def author_query_to_paper_query(query: AuthorSearchQuery, available_fields: PaperDataSelector, required_fields: PaperDataSelector) -> PaperSearchQuery:
            paper_selector = PaperDataSelector.parse_obj({'authors': query.selector.dict()})
            new_paper_selector = (paper_selector & available_fields) | required_fields
            #Since paper queries are a superset of author queries
            return PaperSearchQuery.parse_obj({
                'query': query.query.dict(),
                'selector': new_paper_selector.dict()
            })

        def get_institution_queries(query: AuthorSearchQuery) -> List[Dict[str, Any]]:
            institutions =[]
            def store_institution_callback(dict_structure):
                institutions.append(dict_structure)
            execute_callback_on_tag(query.dict()['query'], 'institution', store_institution_callback)
            execute_callback_on_tag(query.dict()['query'], 'institutionid', store_institution_callback)
            return institutions
        
        class Strategy(Enum):
            AuthorSearch = 'AuthorSearch'
            PaperSearch = 'PaperSearch'
            PaperSearchThenInstitutionSearches = 'PaperSearchThenInstitutionSearches'
            PaperSearchThenAuthorSearches = 'PaperSearchThenAuthorSearches'
            PaperSearchThenInstitutionSearchesThenAuthorSearches = 'PaperSearchThenInstitutionSearchesThenAuthorSearches'
        
        if query.selector in self.scopus_author_search.available_fields:
            try:
                await self.scopus_author_search(query)
                strategy = Strategy.AuthorSearch
            except ScopusQueryError:
                strategy = None
            except TagNotFound:
                strategy = None
        else:
            strategy = None
        if strategy is None:
            institution_queries = get_institution_queries(query)
            if query.selector in self.paper_fields:
                if len(institution_queries) == 0:
                    strategy = Strategy.PaperSearch
                else:
                    strategy = Strategy.PaperSearchThenInstitutionSearches
            
            else:
                if len(institution_queries) == 0:
                    strategy = Strategy.PaperSearchThenAuthorSearches
                else:
                    strategy = Strategy.PaperSearchThenInstitutionSearchesThenAuthorSearches
        assert strategy is not None
    
        async def get_metadata() -> MetadataType:
            def merge_metadatas(metadatas: List[MetadataType]) -> MetadataType:
                new_metadata = {'requests': {}}
                for metadata in metadatas:
                    metadata_dict = metadata.dict()
                    requests = metadata_dict['requests']
                    for request, details in requests.items():
                        if request in new_metadata['requests']:
                            new_request_details = new_metadata['requests'][request]
                            reqd = details['requests_required']
                            new_reqd = new_request_details['requests_required']
                            new_metadata['requests'][request]['requests_required'] = new_reqd + reqd

                            requests_remaining = details['requests_remaining']
                            new_requests_remaining = new_request_details['requests_remaining']
                            new_metadata['requests'][request]['requests_remaining'] = min(requests_remaining, new_requests_remaining)
                        else:
                            new_metadata['requests'][request] = details
                return MetadataType.parse_obj(new_metadata)
            
            async def get_inst_metadatas(inst_queries) -> List[MetadataType]:
                inst_metadatas = []
                for institution_query in institution_queries:
                    institution_search = InstitutionSearchQuery.parse_obj({
                        'query': institution_query,
                        'selector': {
                            'name': True,
                            'id': {
                                'scopus_id': True
                            }
                        }
                    })
                    inst_data_iter = await self.scopus_institution_search(institution_search)
                    inst_metadatas.append(await inst_data_iter.metadata())
                return inst_metadatas
            
            async def get_auth_metadata() -> MetadataType:
                author_search = AuthorSearchQuery.parse_obj({
                    'query': {
                        'tag': 'authorid',
                        'operator': {
                            'tag': 'equal',
                            'value': '7404572266'
                        }
                    },
                    'selector': {
                        'id': {
                            'scopus_id': True
                        }
                    }
                })
                data_iter = await self.scopus_author_search(author_search)
                return await data_iter.metadata()
            
            async def get_unbounded_author_metadata() -> MetadataType:
                fake_author_metadata = await get_auth_metadata()
                requests_available = fake_author_metadata.requests['author_search'].requests_available
                author_metadata = MetadataType.parse_obj({
                    'requests': {
                        'author_search': {
                            'requests': {
                                'requests_required': {
                                    'lower_bound': 0,
                                    'upper_bound': None
                                },
                                'requests_available': requests_available
                            }
                        }
                    }
                })
                return author_metadata


            if strategy == Strategy.AuthorSearch:
                data_iter = await self.scopus_author_search(query)
                return await data_iter.metadata()
            elif strategy == Strategy.PaperSearch:
                data_iter = await self.scopus_paper_search(query)
                return await data_iter.metadata()
            elif strategy == Strategy.PaperSearchThenInstitutionSearches:
                paper_data_iter = await self.scopus_paper_search(query)
                paper_metadata = await paper_data_iter.metadata()
                inst_metadatas = await get_inst_metadatas(institution_queries)
                metadatas = [paper_metadata] + inst_metadatas
                new_metadata = merge_metadatas(metadatas)
                return new_metadata
            elif strategy == Strategy.PaperSearchThenAuthorSearches:
                paper_data_iter = await self.scopus_paper_search(query)
                paper_metadata = await paper_data_iter.metadata()
                author_metadata = await get_unbounded_author_metadata()
                return await merge_metadatas([paper_metadata, author_metadata])

            elif strategy == Strategy.PaperSearchThenInstitutionSearchesThenAuthorSearches:
                paper_data_iter = await self.scopus_paper_search(query)
                paper_metadata = await paper_data_iter.metadata()
                inst_metadatas = await get_inst_metadatas(institution_queries)
                author_metadata = await get_unbounded_author_metadata()
                return await merge_metadatas([paper_metadata, author_metadata] + inst_metadatas)
            else:
                raise ValueError('Unknown strategy')
            
        """
        if (native_author_query is not None) and (native_author_query.metadata['author_search'] < SEARCH_MAX_ENTRIES/25):
            metadata = native_author_query.metadata
        else:
            required_author_fields = PaperDataSelector.parse_obj({
                'authors': {
                    'preferred_name': {
                        'surname': True,
                        'given_names': True
                    },
                    'id':{
                        'scopus_id': True
                    },
                    'other_institutions': {
                        'id':{
                            'scopus_id': True
                        },
                    }
                }
            })
            paper_query = author_query_to_paper_query(query, self.scopus_paper_search.available_fields, required_author_fields)
            native_paper_query = await self.scopus_paper_search.get_native_query(paper_query) # actual_request
            native_paper_query_request_no = native_paper_query.metadata['scopus_search']
            metadata = native_paper_query.metadata
            metadata['institution_search'] = 1
        """

        async def make_coroutine() -> List[AuthorData]:
            def get_unique_authors(query: AuthorSearchQuery, papers: List[PaperData], inst_mapper: List[Tuple[Any, List[InstitutionData]]]) -> List[AuthorData]:
                def construct_author_in_query(query: AuthorSearchQuery, inst_mapper: List[Tuple[Any, List[InstitutionData]]]) -> Callable[[AuthorData], Optional[AuthorData]]:
                    def get_all_insts_from_inst_mapper(inst_mapper: List[Tuple[Any, List[InstitutionData]]]) -> List[InstitutionData]:
                        total_inst = []
                        for _, inst_vs in inst_mapper:
                            total_inst += inst_vs
                        return total_inst

                    query_institutions = get_all_insts_from_inst_mapper(inst_mapper)

                    def author_in_query(author: AuthorData) -> Optional[AuthorData]:
                        def add_institutions_to_author(author: AuthorData, institutions: List[InstitutionData]) -> AuthorData:
                            def get_more_institution_details(institution: Optional[InstitutionData], institutions: List[InstitutionData]):
                                def get_institution_from_id(id: str, institutions: List[InstitutionData]) -> Optional[InstitutionData]:
                                    for institution in institutions:
                                        if institution.id is not None and institution.id.scopus_id == id:
                                            return institution
                                    return None
                                if institution is not None:
                                    inst_id = institution.id.scopus_id
                                    if inst_id is not None:
                                        return get_institution_from_id(inst_id, institutions)
                                return None

                            new_author = deepcopy(author)
                            if hasattr(author, 'institution_current'):
                                inst_current = author.institution_current
                                new_inst_current = get_more_institution_details(inst_current, institutions)
                                
                                if new_inst_current is not None:
                                    new_author.institution_current = new_inst_current
                            if hasattr(author, 'other_institutions'):
                                for i, other_institution in enumerate(author.other_institutions):
                                    new_other_institution = get_more_institution_details(other_institution, institutions)
                                    if new_other_institution is not None:
                                        new_author.other_institutions[i] = new_other_institution

                            return new_author
                        
                        def author_matches_query(query: AuthorSearchQuery, author: AuthorData) -> bool:
                            def author_matches_query_inner(
                                institution_ids: List[str],
                                author_name: Optional[str],
                                author_id: Optional[str]
                            ) -> Callable[[AuthorSearchQuery], bool]:
                                def query_to_term(query) -> bool:
                                    def get_institution_ids_from_mapper(inst_mapper, query) -> List[str]:
                                        for i in inst_mapper:
                                            if i[0] == query:
                                                return [institution.id.scopus_id for institution in i[1] if institution.id is not None]
                                        return []
                                    def make_string_term(body_string: Optional[str], q_value: str, operator: str) -> bool:
                                        if body_string is None:
                                            return False
                                        else:
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
                                    elif query['tag'] == 'author':
                                        operator = query['operator']
                                        value = operator['value']
                                        return make_string_term(author_name, value, operator)
                                    elif query['tag'] == 'authorid':
                                        operator = query['operator']
                                        value = operator['value']
                                        return make_string_term(author_id, value, operator)
                                    elif query['tag'] == 'institution':
                                        operator = query['operator']
                                        value = operator['value']
                                        query_institution_ids = get_institution_ids_from_mapper(inst_mapper, query)
                                        return any([auth_inst_id in query_institution_ids for auth_inst_id in institution_ids])
                                    elif query['tag'] == 'institutionid':
                                        operator = query['operator']
                                        value = operator['value']
                                        query_institution_ids = get_institution_ids_from_mapper(inst_mapper, query)
                                        return any([auth_inst_id in query_institution_ids for auth_inst_id in institution_ids])
                                    elif query['tag'] == 'year':
                                        return True
                                    elif query['tag'] == 'keyword':
                                        return True
                                    elif query['tag'] == 'abstract':
                                        return True
                                    elif query['tag'] == 'title':
                                        return True
                                    elif query['tag'] == 'topic':
                                        return True
                                    else:
                                        tag = query['tag']
                                        raise ValueError(f'Unknown tag: {tag}')

                                return query_to_term

                            institutions = author.other_institutions
                            if hasattr(author, 'institution_current'):
                                if author.institution_current is not None:
                                    institutions.append(author.institution_current)
                            institution_ids = [inst.id.scopus_id for inst in institutions if inst.id.scopus_id is not None]

                            return author_matches_query_inner(institution_ids,author.preferred_name.surname, author.id.scopus_id)(query.dict()['query'])

                        new_author = add_institutions_to_author(author, query_institutions)
                        full_query = AuthorSearchQuery.parse_obj({
                            'query': {
                                'tag': 'or',
                                'fields_': [query.dict()['query']]
                            }
                        })
                        match = author_matches_query(full_query, new_author)
                        if match:
                            return new_author
                        else:
                            return None
                    
                    return author_in_query

                author_in_query = construct_author_in_query(query, inst_mapper)

                unique_authors = {}
                for paper in papers:
                    for author in paper.authors:
                        if author.id.scopus_id not in unique_authors:
                            new_author = author_in_query(author)
                            if new_author:
                                unique_authors[new_author.id.scopus_id] = new_author
                return list(unique_authors.values())


            async def get_institutions_from_query(query: AuthorSearchQuery) -> List[Tuple[Any, List[InstitutionData]]]:
                institutions = get_institution_queries(query)
                inst_mapper = []
                all_insts = []
                for institution in institutions:
                    return_insts = await self.scopus_institution_search(InstitutionSearchQuery.parse_obj({
                        'query': institution,
                        'selector': {
                            'name': True,
                            'id': {
                                'scopus_id': True
                            }
                        }
                    })) # actual_request
                    inst_mapper.append((institution, return_insts))
                    all_insts += return_insts
                return inst_mapper

            if (native_author_query is not None) and (native_author_query.metadata['author_search'] < SEARCH_MAX_ENTRIES/25):
                results = await self.scopus_author_search.get_data_from_native_query(query, native_author_query) # actual_request
                new_results = results
            else:
                results = await self.scopus_paper_search.get_data_from_native_query(paper_query, native_paper_query) # actual_request
                inst_mapper = await get_institutions_from_query(query) # built in actual_request
                new_results = get_unique_authors(query, results, inst_mapper)
                if query.selector not in self.paper_and_institution_fields:
                    author_ids = [author.id.scopus_id for author in new_results if author.id is not None]
                    binned_author_ids = bin_items(author_ids, 25)
                    new_results = []
                    for id_set in binned_author_ids:
                        query_dict = {
                            'query': {
                                'tag': 'or',
                                'fields_': [{
                                    'tag': 'authorid',
                                    'operator': {
                                        'tag': 'equal',
                                        'value': {
                                            'scopus_id': auth_id
                                        }
                                    }
                                } for auth_id in id_set]
                            },
                            'selector': query.selector.dict()
                        }
                        new_results += await self.scopus_author_search(AuthorSearchQuery.parse_obj(query_dict)) # actual_request
            return new_results
        return make_coroutine, metadata

    async def _post_process(self, query: AuthorSearchQuery, data: List[AuthorData]) -> List[AuthorData]:
        model = AuthorData.generate_model_from_selector(query.selector)
        output = [model.parse_obj(i.dict()) for i in data]
        return output


class OptimisedScopusBackend(Backend):
    def __init__(
        self, 
        scopus_backend: ScopusBackend, 
        pubmed_backend: PubmedBackend
    ) -> None:
        self.scopus_backend = scopus_backend
        self.pubmed_backend = pubmed_backend
    
    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            self.scopus_backend.paper_search_engine(), 
            self.pubmed_backend.paper_search_engine()
        )

    def author_search_engine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine(
            self.scopus_backend.paper_search_engine(),
            self.scopus_backend.author_search_engine(),
            self.scopus_backend.institution_search_engine()
        )
    
    def institution_search_engine(self) -> ScopusInstitutionSearchQueryEngine:
        return self.scopus_backend.institution_search_engine()
