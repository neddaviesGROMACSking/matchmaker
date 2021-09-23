from pydantic import BaseModel
from typing import Generic, Type, TypeVar

from matchmaker.query_engine.abstract import AbstractQueryEngine

class AbstractNativeQuery:
    def _count_api_calls(self):
        raise NotImplementedError('Calling method on abstract base class')
    def _count_api_calls_by_method(self, method: str):
        raise NotImplementedError('Calling method on abstract base class')


Query = TypeVar('Query')
Data = TypeVar('Data')
NativeQuery = TypeVar('NativeQuery', bound=AbstractNativeQuery)
NativeData = TypeVar('NativeData')


class SlightlyLessAbstractQueryEngine(Generic[Query, Data, NativeQuery, NativeData], AbstractQueryEngine[Query, Data]):
    def _query_to_native(self, query: Query) -> NativeQuery:
        raise NotImplementedError('Calling method on abstract base class')

    def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')

    def _post_process(self, query: Query, data: NativeData) \
            -> NativeData:
        raise NotImplementedError('Calling method on abstract base class')

    def _data_from_native(self, data: NativeData) -> Data:
        raise NotImplementedError('Calling method on abstract base class')

    def __call__(self, query: Query) -> Data:
        nd = self._run_native_query(self._query_to_native(query))
        return self._data_from_native(self._post_process(query, nd))
