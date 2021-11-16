
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery
from typing import Optional, Tuple, Callable, Awaitable, Dict, List, Generic, TypeVar, Union, Any

from dataclasses import dataclass

from dataclasses import dataclass

from typing import Awaitable, Callable, Dict, Generic, Optional, Tuple, TypeVar

from matchmaker.query_engine.data_types import AuthorData, PaperData, InstitutionData
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.slightly_less_abstract import (
    AbstractNativeQuery,
    SlightlyLessAbstractQueryEngine,
)

NativeData = TypeVar('NativeData')
@dataclass
class BaseNativeQuery(Generic[NativeData], AbstractNativeQuery):
    coroutine_function: Callable[[], Awaitable[NativeData]]
    metadata: Dict[str, int]
    def count_api_calls(self):
        return sum(self.metadata.values())
    def count_api_calls_by_method(self, method: str):
        return self.metadata[method]

Query = TypeVar('Query')
Data = TypeVar('Data')



class BaseBackendQueryEngine(
    Generic[Query, NativeData, Data], 
    SlightlyLessAbstractQueryEngine[Query, BaseNativeQuery[NativeData], NativeData, Data]
):    
    async def _query_to_awaitable(self, query: Query) -> Tuple[Callable[[], Awaitable[NativeData]], Dict[str, int]]:
        raise NotImplementedError('This method is required for query_to_native')
    async def _query_to_native(self, query: Query) -> BaseNativeQuery[NativeData]:
        awaitable, metadata = await self._query_to_awaitable(query)
        return BaseNativeQuery(awaitable, metadata)
    
    async def _run_native_query(self, query: BaseNativeQuery[NativeData]) -> NativeData:
        return await query.coroutine_function()
    
    async def _post_process(self, query: Query, data: NativeData) -> Data:
        raise NotImplementedError('Calling method on abstract base class')

    async def __call__(self, query: Query) -> Data:
        nd = await self._run_native_query(await self._query_to_native(query))
        return await self._post_process(query, nd)
    
    #Put post process as no op


class BasePaperSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[PaperSearchQuery, NativeData, PaperData]
):
    pass


class BaseAuthorSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[AuthorSearchQuery, NativeData, AuthorData]
):
    pass

class BaseInstitutionSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[InstitutionSearchQuery, NativeData, InstitutionData]
):
    pass
