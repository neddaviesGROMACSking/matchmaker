from dataclasses import dataclass
from asyncio import coroutine, Future, get_running_loop
from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery, SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.data_types import PaperData, AuthorData
from typing import Dict, TypeVar,Generic, Tuple

@dataclass
class BaseNativeQuery(AbstractNativeQuery):
    awaitable: coroutine
    metadata: Dict[str, str]
    client_future: Future
    def _count_api_calls(self):
        return len(self.metadata)
    def _count_api_calls_by_method(self, method: str):
        return self.metadata[method]

Query = TypeVar('Query')
Data = TypeVar('Data')
NativeData = TypeVar('NativeData')

class BaseBackendQueryEngine(
    Generic[Query, Data, NativeData], 
    SlightlyLessAbstractQueryEngine[Query, Data, BaseNativeQuery, NativeData]
):
    async def _query_to_awaitable(self, query: Query, client_future: Future) -> Tuple[coroutine, Dict[str, str]]:
        raise NotImplementedError('This method is required for query_to_native')
    async def _query_to_native(self, query: Query) -> BaseNativeQuery:
        loop = get_running_loop()
        client_future = loop.create_future()
        awaitable, metadata = await _query_to_awaitable(query, client_future)
        return BaseNativeQuery(awaitable, metadata, client_future)

    async def _run_native_query(self, query: BaseNativeQuery) -> NativeData:
        async with httpx.AsyncClient() as client:
            query.client_future.set_result(client)
            results = await query.awaitable
        return results

NativeData = TypeVar('NativeData')
class BasePaperSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[PaperSearchQuery, PaperData, NativeData]
):
    pass

NativeData = TypeVar('NativeData')
class BaseAuthorSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[AuthorSearchQuery, AuthorData, NativeData]
):
    pass

NativeData = TypeVar('NativeData')
class BasePaperDetailsQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[PaperDetailsQuery, PaperData, NativeData]
):
    pass

NativeData = TypeVar('NativeData')
class BaseAuthorDetailsQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[AuthorDetailsQuery, AuthorData, NativeData]
):
    pass