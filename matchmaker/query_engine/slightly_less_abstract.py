from pydantic import BaseModel
from typing import AsyncIterator, Callable, Generic, Type, TypeVar, List, Optional

from matchmaker.query_engine.abstract import AbstractQueryEngine

Metadata = TypeVar('Metadata')

# Native data bound to async iterator?

class AbstractNativeQuery(Generic[Metadata]):
    def count_api_calls(self):
        raise NotImplementedError('Calling method on abstract base class')
    def count_api_calls_by_method(self, method: str):
        raise NotImplementedError('Calling method on abstract base class')
    async def get_metadata(self) -> Metadata:
        raise NotImplementedError('Calling method on abstract base class')

Query = TypeVar('Query')
Data = TypeVar('Data', bound = AsyncIterator)
DataElement = TypeVar('DataElement')
NativeQuery = TypeVar('NativeQuery', bound=AbstractNativeQuery)
NativeData = TypeVar('NativeData')

class DataOut(Generic[NativeQuery, Data, DataElement, Metadata], AsyncIterator):
    _async_iter: Data
    _get_metadata: Callable[[], Metadata]
    _list: Optional[List[DataElement]]
    def __init__(self, native_query: NativeQuery, data_async_iterator: Data) -> None:
        self._async_iter = data_async_iterator
        self._native_query = native_query
        self._list = None
    def __aiter__(self):
        return self._async_iter.__aiter__()
    async def __anext__(self):
        return await self._async_iter.__anext__()
    async def get_metadata(self) -> Metadata:
        return await self._native_query.get_metadata()
    async def __getitem__(self, index: int):
        if self._list is None:
            self._list = [i async for i in self._async_iter]
        return self._list[index]

class SlightlyLessAbstractQueryEngine(
    Generic[Query, NativeQuery, NativeData, Data, DataElement, Metadata], 
    AbstractQueryEngine[Query, Data]
):
    async def _query_to_native(self, query: Query) -> NativeQuery:
        raise NotImplementedError('Calling method on abstract base class')
    async def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')
    async def _post_process(self, query: Query, data: NativeData) \
            -> Data:
        raise NotImplementedError('Calling method on abstract base class')
    async def __call__(self, query: Query) -> DataOut:
        nq = await self._query_to_native(query)
        nd = await self._run_native_query(nq)
        data_iter = await self._post_process(query, nd)
        return DataOut[NativeQuery, Data, DataElement, Metadata](nq, data_iter)

    async def get_native_query(self, query: Query) -> NativeQuery:
        return await self._query_to_native(query)
    async def get_data_from_native_query(self, query: Query, native_query: NativeQuery):
        nd = await self._run_native_query(native_query)
        return await self._post_process(query, nd)
