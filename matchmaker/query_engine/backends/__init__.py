from asyncio import Future, coroutine, get_running_loop
import asyncio
from dataclasses import dataclass
import time
from typing import Awaitable, Callable, Dict, Generic, Iterable, Iterator, Optional, Tuple, TypeVar, Any, Union
import uuid

from aiohttp import ClientSession, TCPConnector
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
import warnings
from typing import AsyncIterator
from pydantic import BaseModel

class MetadataType(BaseModel):
    class Requests(BaseModel):
        class Range(BaseModel):
            lower_bound: int
            upper_bound: int
        requests_required: Union[int, Range]
        requests_remaining: Optional[int]
    requests: Dict[str, Requests] = {}
    no_results: Optional[int] = None

#MetadataType = Dict[str, Tuple[int, Optional[int]]]
GetMetadata = Callable[[], Awaitable[MetadataType]]
NativeData = TypeVar('NativeData')
GetData = TypeVar('GetData', bound = Callable[..., Any])

class BaseNativeQuery(Generic[NativeData, GetData], AbstractNativeQuery[MetadataType]):
    coroutine_function: GetData
    _get_metadata: Callable[[], Awaitable[MetadataType]]
    _metadata: Optional[MetadataType]
    def __init__(
        self, 
        get_data: GetData, 
        get_metadata: GetMetadata
    ) -> None:
        self.coroutine_function = get_data
        self._get_metadata = get_metadata
        self._metadata = None
    async def metadata(self):
        return await self._get_metadata()
    async def count_api_calls(self):
        if self._metadata is None:
            self._metadata = await self.metadata()
        return sum(self._metadata.values())
    async def count_api_calls_by_method(self, method: str):
        if self._metadata is None:
            self._metadata = await self.metadata()
        return self._metadata[method]

   

Query = TypeVar('Query')
ProcessedData = TypeVar('ProcessedData', bound = AsyncIterator)
NativeQuery = TypeVar('NativeQuery', bound = BaseNativeQuery)
DataElement = TypeVar('DataElement')

class BaseBackendQueryEngine(Generic[Query, NativeQuery, NativeData, ProcessedData, DataElement], 
    SlightlyLessAbstractQueryEngine[Query, NativeQuery, NativeData, ProcessedData, DataElement, MetadataType]
):
    pass


class BasePaperSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData], 
    BaseBackendQueryEngine[PaperSearchQuery, NativeQuery, NativeData, ProcessedData, PaperData]
):
    pass


class BaseAuthorSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData], 
    BaseBackendQueryEngine[AuthorSearchQuery, NativeQuery, NativeData, ProcessedData, AuthorData]
):
    pass

class BaseInstitutionSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData], 
    BaseBackendQueryEngine[InstitutionSearchQuery, NativeQuery, NativeData, ProcessedData, InstitutionData]
):
    pass


DataForProcess = TypeVar('DataForProcess')
ProcessedData = TypeVar('ProcessedData')
class ProcessDataIter(AsyncIterator, Generic[DataForProcess, ProcessedData]):
    _iterator: Iterator[DataForProcess]
    _processor: Callable[[DataForProcess], Awaitable[ProcessedData]]
    def __init__(self, iterator: Iterator[DataForProcess], processing_func: Callable[[DataForProcess], Awaitable[ProcessedData]]) -> None:
        self._iterator = iterator
        self._processor = processing_func
        super().__init__()
    async def __anext__(self):
        try:
            next_item = next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration
        return await self._processor(next_item)
    def __aiter__(self) -> AsyncIterator[DataForProcess]:
        return self

class AsyncProcessDataIter(AsyncIterator, Generic[DataForProcess, ProcessedData]):
    _iterator: AsyncIterator[DataForProcess]
    _processor: Callable[[DataForProcess], Awaitable[ProcessedData]]
    def __init__(self, iterator: AsyncIterator[DataForProcess], processing_func: Callable[[DataForProcess], Awaitable[ProcessedData]]) -> None:
        self._iterator = iterator
        self._processor = processing_func
        super().__init__()
    async def __anext__(self):
        next_item = await self._iterator.__anext__()
        return await self._processor(next_item)
    def __aiter__(self) -> AsyncIterator[DataForProcess]:
        return self._iterator
