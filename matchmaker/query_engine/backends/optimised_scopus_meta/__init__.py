from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend

from matchmaker.query_engine.data_types import AuthorData, PaperData, InstitutionData
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend
from typing import Optional, Tuple, Callable, Awaitable, Dict, List, Generic, TypeVar
from asyncio import get_running_loop, gather
from math import ceil
from dataclasses import dataclass
NativeData = TypeVar('NativeData')
@dataclass
class BaseNativeQuery(Generic[NativeData], AbstractNativeQuery):
    coroutine_function: Callable[[], Awaitable[NativeData]]
    metadata: Dict[str, int]
    def count_api_calls(self):
        return sum(self.metadata.values())
    def count_api_calls_by_method(self, method: str):
        return self.metadata[method]

async def get_doi_list_from_data(papers: List[PaperData]) -> List[str]:
    return []

async def get_doi_query_from_list(dois: List[str]) -> PaperSearchQuery:
    return PaperSearchQuery()

async def get_dois_remaining(scopus_dois: List[str], pubmed_dois: List[str]) -> List[str]:
    return []

class PaperSearchQueryEngine(
    SlightlyLessAbstractQueryEngine[PaperSearchQuery, BaseNativeQuery[PaperData], PaperData, PaperData, PaperData]):
    def __init__(
        self, 
        scopus_paper_search,
        scopus_paper_standard_search,
        pubmed_paper_search,
        complete_search_request_limit = 100,
        overall_request_limit = 100,
    ) -> None:
        self.scopus_paper_search = scopus_paper_search
        self.scopus_paper_standard_search = scopus_paper_standard_search
        self.pubmed_paper_search = pubmed_paper_search
        self.complete_search_request_limit = complete_search_request_limit
        self.overall_request_limit = overall_request_limit
    
    async def _query_to_awaitable(self, query: PaperSearchQuery) -> Tuple[Callable[[], Awaitable[List[PaperData]]], Dict[str, int]]:
        # Step 1 - get standard results
        full_native_query = await self.scopus_paper_search.get_native_query(query)
        full_native_request_no = full_native_query.metadata['scopus_search']
        standard_native_query = await self.scopus_paper_standard_search.get_native_query(query) 
        standard_native_request_no = standard_native_query.metadata['scopus_search']
        # For pubmed it's always the same, so this can be a good estimate
        pubmed_native_query = await self.pubmed_paper_search.get_native_query(query)
        metadata = {
            'scopus_search': full_native_request_no + standard_native_request_no,
            **pubmed_native_query.metadata
        }
        async def make_coroutine() -> List[PaperData]:
            # Step 1 - get standard results
            standard_data = await self.scopus_paper_standard_search.get_data_from_native_query(standard_native_query)
            doi_list_scopus = await get_doi_list_from_data(standard_data)
            doi_query_pubmed = await get_doi_query_from_list(doi_list_scopus)
            # Step 2 - get pubmed data from dois
            pubmed_data = await self.pubmed_paper_search(doi_query_pubmed)
            doi_list_pubmed = await get_doi_list_from_data(pubmed_data)
            dois_remaining = await get_dois_remaining(doi_list_scopus, doi_list_pubmed)
            complete_no_requests = len(dois_remaining)//25 +2

            # Step 3 - get estimate for returning to scopus for more info
            #pubmed will do same as always number of requests!
            #But nature of the query depends upon the results of standard_native_data

            if self.complete_search_request_limit < complete_no_requests:
                return pubmed_data
            else:
                def bin_dois(dois: List[str], bin_limit: int = 25) -> List[List[str]]:
                    binned_dois = []
                    current_bin_index = 0
                    for i in dois:
                        if current_bin_index < len(binned_dois):
                            binned_dois.append([])
                        binned_dois[current_bin_index].append(i)
                        if binned_dois[current_bin_index] >= bin_limit:
                            current_bin_index += 1
                    return binned_dois
                #split doi list into blocks of 25 (25 per request),
                # to reduce url length per length
                binned_dois = bin_dois(dois_remaining)

                async def get_paper_data_from_dois(dois):
                    doi_query_scopus = await get_doi_query_from_list(dois_remaining)
                    return await self.scopus_paper_search(doi_query_scopus)
                results = gather(*list(map(get_paper_data_from_dois, binned_dois)))
                concat_results = []
                for i in results:
                    concat_results += i
                return concat_results

        return make_coroutine, metadata
    
    async def _query_to_native(self, query: PaperSearchQuery) -> BaseNativeQuery[List[PaperData]]:
        awaitable, metadata = await self._query_to_awaitable(query)
        return BaseNativeQuery(awaitable, metadata)
    
    async def _post_process(self, query: PaperSearchQuery, data: List[PaperData]) -> List[PaperData]:
        return data

    async def _data_from_processed(self, data: List[PaperData]) -> List[PaperData]:
        return data

class OptimisedScopusBackend(Backend):
    def __init__(
        self, 
        scopus_backend: ScopusBackend, 
        pubmed_backend: PubmedBackend
    ):
        self.scopus_backend = scopus_backend
        self.pubmed_backend = pubmed_backend
    
    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            self.scopus_backend.paper_search_engine(full_view = True), 
            self.scopus_backend.paper_search_engine(full_view = False),
            self.pubmed_backend.paper_search_engine()
        )

