from pydantic import BaseModel
from typing import Generic, Type, TypeVar

from matchmaker.query_engine.query_types import Query, \
        PaperQuery, AuthorQuery, AuthorByIDQuery, CoauthorByIDQuery
from matchmaker.query_engine.data_types import Data


NativeQuery = TypeVar('NativeQuery', bound=BaseModel)
NativeData = TypeVar('NativeData', bound=BaseModel)


class AbstractQueryEngine(Generic[NativeQuery, NativeData]):
    def _paper_query_to_native(self, query: PaperQuery) -> NativeQuery:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support PaperQuery')

    def _author_query_to_native(self, query: AuthorQuery) -> NativeQuery:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support AuthorQuery')

    def _author_by_id_query_to_native(self, query: AuthorByIDQuery) \
            -> NativeQuery:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support AuthorByIDQuery')

    def _coauthor_by_id_query_to_native(self, query: CoauthorByIDQuery) \
            -> NativeQuery:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support CoauthorByIDQuery')

    def _query_to_native(self, query: Query) -> NativeQuery:
        if isinstance(query, PaperQuery):
            return self._paper_query_to_native(query)
        elif isinstance(query, AuthorQuery):
            return self._author_query_to_native(query)
        elif isinstance(query, AuthorByIDQuery):
            return self._author_by_id_query_to_native(query)
        elif isinstance(query, CoauthorByIDQuery):
            return self._coauthor_by_id_query_to_native(query)
        else:
            raise ValueError(f'Unknown query type {query.__class__.__name__}')

    def _run_native_query(self, query: NativeQuery) -> NativeData:
        raise NotImplementedError('Subclass implements this')

    def _post_process_paper_query(self, query: PaperQuery, data: NativeData) \
            -> NativeData:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support PaperQuery')

    def _post_process_author_query(self, query: AuthorQuery,
                                   data: NativeData) -> NativeData:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support AuthorQuery')

    def _post_process_author_by_id_query(self, query: AuthorByIDQuery,
                                         data: NativeData) -> NativeData:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support AuthorByIDQuery')

    def _post_process_coauthor_by_id_query(self, query: CoauthorByIDQuery,
                                           data: NativeData) -> NativeData:
        raise NotImplementedError(
            f'{self.__class__.__name__} doesn\'t support CoauthorByIDQuery')

    def _post_process(self, query: Query, data: NativeData) -> NativeData:
        if isinstance(query, PaperQuery):
            return self._post_process_paper_query(query, data)
        elif isinstance(query, AuthorQuery):
            return self._post_process_author_query(query, data)
        elif isinstance(query, AuthorByIDQuery):
            return self._post_process_author_by_id_query(query, data)
        elif isinstance(query, CoauthorByIDQuery):
            return self._post_process_coauthor_by_id_query(query, data)
        else:
            raise ValueError(f'Unknown query type {query.__class__.__name__}')

    def _data_from_native(self, data: NativeData) -> Data:
        raise NotImplementedError('Subclass implements this')

    def __call__(self, query: Query) -> Data:
        nd = self._run_native_query(self._query_to_native(query))
        return self._data_from_native(self._post_process(query, nd))
