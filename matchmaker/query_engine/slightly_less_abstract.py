from pydantic import BaseModel
from typing import AsyncIterator, Awaitable, Callable, Generic, Type, TypeVar, List, Optional

from matchmaker.query_engine.abstract import AbstractQueryEngine

Metadata = TypeVar('Metadata')

# Native data bound to async iterator?

class AbstractNativeQuery(Generic[Metadata]):
    def count_api_calls(self):
        raise NotImplementedError('Calling method on abstract base class')
    def count_api_calls_by_method(self, method: str):
        raise NotImplementedError('Calling method on abstract base class')
    async def metadata(self) -> Metadata:
        raise NotImplementedError('Calling method on abstract base class')

Query = TypeVar('Query')
ProcessedData = TypeVar('ProcessedData', bound = AsyncIterator)
DataElement = TypeVar('DataElement')
NativeQuery = TypeVar('NativeQuery', bound=AbstractNativeQuery)
NativeData = TypeVar('NativeData')

class Data(Generic[NativeQuery, ProcessedData, DataElement, Metadata], AsyncIterator):
    _get_data: Callable[[], Awaitable[ProcessedData]]
    _get_metadata: Callable[[], Metadata]
    _list: Optional[List[DataElement]]
    _async_iter: Optional[ProcessedData]
    def __init__(self, native_query: NativeQuery, get_data: Callable[[], Awaitable[ProcessedData]]) -> None:
        self._get_data = get_data
        self._native_query = native_query
        self._list = None
        self._async_iter = None
    def __aiter__(self):
        return self
    async def __anext__(self):
        if self._async_iter is None:
            self._async_iter = await self._get_data()
        return await self._async_iter.__anext__()
    async def metadata(self) -> Metadata:
        return await self._native_query.metadata()
    async def __getitem__(self, index: int):
        if self._list is None:
            self._list = [i async for i in self]
        return self._list[index]

class SlightlyLessAbstractQueryEngine(
    Generic[Query, NativeQuery, NativeData, ProcessedData, DataElement, Metadata], 
    AbstractQueryEngine[Query, Data]
):
    async def _query_to_native(self, query: Query) -> NativeQuery:
        raise NotImplementedError('Calling method on abstract base class')
    async def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')
    async def _post_process(self, query: Query, data: NativeData) \
            -> ProcessedData:
        raise NotImplementedError('Calling method on abstract base class')
    async def __call__(self, query: Query) -> Data:
        nq = await self._query_to_native(query)
        async def get_data():
            nd = await self._run_native_query(nq)
            data_iter = await self._post_process(query, nd)
            return data_iter
        return Data[NativeQuery, ProcessedData, DataElement, Metadata](nq, get_data)
