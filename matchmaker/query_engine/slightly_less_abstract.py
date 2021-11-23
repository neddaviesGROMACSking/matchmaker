from pydantic import BaseModel
from typing import Callable, Generic, Type, TypeVar

from matchmaker.query_engine.abstract import AbstractQueryEngine

"""
Metadata = TypeVar('Metadata')
class AbstractNativeQuery(Generic[Metadata]):
    metadata: Metadata
    async def get_metadata(self):
        raise NotImplementedError
    def count_api_calls(self):
        raise NotImplementedError('Calling method on abstract base class')
    def count_api_calls_by_method(self, method: str):
        raise NotImplementedError('Calling method on abstract base class')
"""

class AbstractNativeQuery:
    def count_api_calls(self):
        raise NotImplementedError('Calling method on abstract base class')
    def count_api_calls_by_method(self, method: str):
        raise NotImplementedError('Calling method on abstract base class')

Query = TypeVar('Query')
Data = TypeVar('Data')
NativeQuery = TypeVar('NativeQuery', bound=AbstractNativeQuery)
NativeData = TypeVar('NativeData')

"""
from typing import List, Optional, Awaitable
DataElement = TypeVar('DataElement')

class DataGetter(Generic[DataElement, Metadata]):
    _get_data: Awaitable[DataElement]
    _get_metadata: Awaitable[Metadata]
    _data: Optional[DataElement]
    _metadata: Optional[Metadata]

    def __init__(
        self, 
        get_data: Awaitable[DataElement], 
        get_metadata: Awaitable[Metadata]
    ) -> None:
        self._get_data = get_data
        self._get_metadata = get_metadata
        self._data = None
        self._metadata = None
    
    async def get_data(self) -> DataElement:
        if self._data is None:
            self._data = await self._get_data
        return self._data
    
    async def get_metadata(self) -> Metadata:
        if self._metadata is None:
            self._metadata = await self._get_metadata
        return self._metadata


#data_getter = await get_paper_engine(query)
#data = await data_getter.get_data()
#metadata = await data_getter.get_metadata()




class SlightlyLessAbstractQueryEngine(Generic[Query, NativeQuery, NativeData, Data], AbstractQueryEngine[Query, Data]):
    async def _query_to_native(self, query: Query) -> NativeQuery:
        raise NotImplementedError('Calling method on abstract base class')
    async def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')
    async def _post_process(self, query: Query, data: NativeData) \
            -> Data:
        raise NotImplementedError('Calling method on abstract base class')
    async def __call__(self, query: Query) -> DataGetter:

        nq = await self._query_to_native(query)

        async def get_metadata():
            return nq.get_metadata()
        
        async def get_data():
            return await self._post_process(query, await self._run_native_query(nq))
        return DataGetter(get_data(), get_metadata())
"""

class SlightlyLessAbstractQueryEngine(Generic[Query, NativeQuery, NativeData, Data], AbstractQueryEngine[Query, Data]):
    async def _query_to_native(self, query: Query) -> NativeQuery:
        raise NotImplementedError('Calling method on abstract base class')
    async def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')
    async def _post_process(self, query: Query, data: NativeData) \
            -> Data:
        raise NotImplementedError('Calling method on abstract base class')
    async def __call__(self, query: Query) -> Data:
        nd = await self._run_native_query(await self._query_to_native(query))
        return await self._post_process(query, nd)
    async def get_native_query(self, query: Query) -> NativeQuery:
        return await self._query_to_native(query)
    async def get_data_from_native_query(self, query: Query, native_query: NativeQuery):
        nd = await self._run_native_query(native_query)
        return await self._post_process(query, nd)
