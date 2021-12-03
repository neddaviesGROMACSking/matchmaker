
from typing import (
    AsyncIterator,
    Awaitable,
    Callable,
    Generic,
    Iterator,
    List,
    Tuple,
    TypeVar,
)
from matchmaker.query_engine.backends import (
    AsyncProcessDataIter,
    BaseBackendQueryEngine,
    BaseNativeQuery,
    GetMetadata,
    BasePaperSearchQueryEngine,
    BaseAuthorSearchQueryEngine,
    BaseInstitutionSearchQueryEngine
)
from matchmaker.query_engine.types.data import AuthorData, InstitutionData, PaperData
from matchmaker.query_engine.types.query import (
    AuthorSearchQuery,
    InstitutionSearchQuery,
    PaperSearchQuery,
)

NativeData = TypeVar('NativeData')
Query = TypeVar('Query')
Data = TypeVar('Data')

class MetaNativeQuery(
    Generic[NativeData], 
    BaseNativeQuery[
        NativeData, 
        Callable[[], Awaitable[NativeData]]
    ]
):
    pass

Query = TypeVar('Query')
ProcessedData = TypeVar('ProcessedData', bound = AsyncIterator)
NativeQuery = TypeVar('NativeQuery', bound = MetaNativeQuery)
DataElement = TypeVar('DataElement')

class MetaQueryEngine(
    Generic[Query, NativeData, Data, ProcessedData, DataElement], 
    BaseBackendQueryEngine[
        Query,
        MetaNativeQuery[NativeData], 
        NativeData, 
        ProcessedData,
        DataElement
    ]
):    
    async def _query_to_awaitable(self, query: Query) -> Tuple[Callable[[], Awaitable[NativeData]], GetMetadata]:
        raise NotImplementedError('This method is required for query_to_native')
    async def _query_to_native(self, query: Query) -> MetaNativeQuery[NativeData]:
        awaitable, metadata = await self._query_to_awaitable(query)
        return MetaNativeQuery(awaitable, metadata)
    
    async def _run_native_query(self, query: MetaNativeQuery[NativeData]) -> NativeData:
        return await query.coroutine_function()



class MetaPaperSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData],
    BasePaperSearchQueryEngine[NativeQuery, NativeData, ProcessedData],
    MetaQueryEngine[PaperSearchQuery, NativeQuery, NativeData, ProcessedData, PaperData],

):
    pass

class MetaAuthorSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData],
    BaseAuthorSearchQueryEngine[NativeQuery, NativeData, ProcessedData],
    MetaQueryEngine[AuthorSearchQuery, NativeQuery, NativeData, ProcessedData, AuthorData],
):
    pass

class MetaInstitutionSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData],
    BaseInstitutionSearchQueryEngine[NativeQuery, NativeData, ProcessedData],
    MetaQueryEngine[InstitutionSearchQuery, NativeQuery, NativeData, ProcessedData, InstitutionData],
):
    pass



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