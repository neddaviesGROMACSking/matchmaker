from typing import List, Tuple, Callable, Awaitable, Dict

from matchmaker.query_engine.backends import (
    BaseAuthorSearchQueryEngine,
    BasePaperSearchQueryEngine,
    RateLimiter,
    NewAsyncClient
)
from matchmaker.query_engine.backends.scopus_api_new import (
    AffiliationSearchQuery,
    ScopusAuthorSearchQuery,
    ScopusSearchQuery,
    ScopusSearchResult,
    affiliation_search_on_query,
    author_search_on_query,
    get_affiliation_query_no_requests,
    get_affiliation_query_remaining_in_cache,
    get_author_query_no_requests,
    get_author_query_remaining_in_cache,
    get_scopus_query_no_requests,
    get_scopus_query_remaining_in_cache,
    scopus_search_on_query,
)
from matchmaker.query_engine.backends.scopus_utils import create_config
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery
from aiohttp import ClientSession
from matchmaker.query_engine.data_types import AuthorData, PaperData
from matchmaker.query_engine.backends.tools import replace_dict_tags, replace_dict_tag
class NotEnoughRequests(Exception):
    pass

def paper_query_to_scopus(query: PaperSearchQuery):
    query_dict = query.dict()['__root__']
    new_query_dict = replace_dict_tags(
        query_dict,
        auth = 'author',
        srctitle = 'journal',
        authorkeyword = 'keyword',
        keyword = 'topic',
        affiliation = 'institution'
    )
    return ScopusSearchQuery.parse_obj(new_query_dict)

def author_query_to_scopus_author(query: AuthorSearchQuery):
    return ScopusAuthorSearchQuery.parse_obj(query.dict()['__root__'])


class PaperSearchQueryEngine(
        BasePaperSearchQueryEngine[List[ScopusSearchResult], List[ScopusSearchResult]]):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        create_config(api_key, institution_token)
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(self, query: PaperSearchQuery, client: NewAsyncClient) -> Tuple[Callable[[NewAsyncClient], Awaitable[List[ScopusSearchResult]]], Dict[str, int]]:
        scopus_search_query = paper_query_to_scopus(query)
        cache_remaining = await get_scopus_query_remaining_in_cache()
        view = 'COMPLETE'
        if cache_remaining > 1:
            no_requests = await get_scopus_query_no_requests(scopus_search_query, client, view = view)
        else:
            raise NotEnoughRequests()
        cache_remaining = await get_scopus_query_remaining_in_cache()
        if no_requests > cache_remaining:
            raise NotEnoughRequests()
        metadata = {
            'scopus_search': no_requests,
        }
        async def make_coroutine(client: ClientSession) -> List[ScopusSearchResult]:
            return await scopus_search_on_query(scopus_search_query, client, view)
        return make_coroutine, metadata
    
    async def _post_process(self, query: PaperSearchQuery, data: List[ScopusSearchResult]) -> List[ScopusSearchResult]:
        print(data[0])
        return data
    
    async def _data_from_processed(self, data: List[ScopusSearchResult]) -> List[PaperData]:
        return [PaperData.parse_obj(i.dict()['__root__']) for i in data]

