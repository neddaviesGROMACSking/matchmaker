
from dataclasses import dataclass
from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)
from typing import Awaitable, Callable, Dict, Generic, Optional, Tuple, TypeVar

from matchmaker.query_engine.backends import (
    BaseBackendQueryEngine,
    BaseNativeQuery,
    GetMetadata,
    BasePaperSearchQueryEngine,
    BaseAuthorSearchQueryEngine,
    BaseInstitutionSearchQueryEngine
)
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery
from matchmaker.query_engine.slightly_less_abstract import (
    AbstractNativeQuery,
    SlightlyLessAbstractQueryEngine,
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
