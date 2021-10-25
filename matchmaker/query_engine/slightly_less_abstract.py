from pydantic import BaseModel
from typing import Generic, Type, TypeVar

from matchmaker.query_engine.abstract import AbstractQueryEngine

class AbstractNativeQuery:
    def count_api_calls(self):
        raise NotImplementedError('Calling method on abstract base class')
    def count_api_calls_by_method(self, method: str):
        raise NotImplementedError('Calling method on abstract base class')


Query = TypeVar('Query')
Data = TypeVar('Data')
NativeQuery = TypeVar('NativeQuery', bound=AbstractNativeQuery)
NativeData = TypeVar('NativeData')
ProcessedNativeData = TypeVar('ProcessedNativeData')

class SlightlyLessAbstractQueryEngine(Generic[Query, NativeQuery, NativeData, ProcessedNativeData, Data], AbstractQueryEngine[Query, Data]):
    def _query_to_native(self, query: Query) -> NativeQuery:
        raise NotImplementedError('Calling method on abstract base class')
    def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')
    def _post_process(self, query: Query, data: NativeData) \
            -> ProcessedNativeData:
        raise NotImplementedError('Calling method on abstract base class')
    def _data_from_processed(self, data: ProcessedNativeData) -> Data:
        raise NotImplementedError('Calling method on abstract base class')
    def __call__(self, query: Query) -> Data:
        nd = self._run_native_query(self._query_to_native(query))
        return self._data_from_processed(self._post_process(query, nd))
    def get_native_query(self, query: Query) -> NativeQuery:
        return self._query_to_native(query)
    def get_data_from_native_query(self, query: NativeQuery):
        nd = self._run_native_query(query)
        return self._data_from_processed(self._post_process(query, nd))
