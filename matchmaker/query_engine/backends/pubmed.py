from pydantic import BaseModel
from typing import Union

from matchmaker.query_engine.query_types import PaperQuery, AuthorQuery, \
        AuthorByIDQuery, CoauthorByIDQuery
from matchmaker.query_engine.data_types import Data
from matchmaker.query_engine.abstract import AbstractQueryEngine


class PubMedPaperQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorByIDQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedCoauthorByIDQuery(BaseModel):
    # TODO: implement this
    pass


PubMedQuery = Union[PubMedPaperQuery, PubMedAuthorQuery,
                    PubMedAuthorByIDQuery, PubMedCoauthorByIDQuery]


class PubMedPaperData(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorData(BaseModel):
    # TODO: implement this
    pass


PubMedData = Union[PubMedPaperData, PubMedAuthorData]


class QueryEngine(AbstractQueryEngine[PubMedQuery, PubMedData]):
    def _paper_query_to_native(self, query: PaperQuery) -> PubMedQuery:
        # TODO: implement this
        pass

    def _author_query_to_native(self, query: AuthorQuery) -> PubMedQuery:
        # TODO: implement this
        pass

    def _author_by_id_query_to_native(self, query: AuthorByIDQuery) \
            -> PubMedQuery:
        # TODO: implement this
        pass

    def _coauthor_by_id_query_to_native(self, query: CoauthorByIDQuery) \
            -> PubMedQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedQuery) -> PubMedData:
        # TODO: implement this
        pass

    def _post_process_paper_query(self, query: PaperQuery,
                                  data: PubMedData) -> PubMedData:
        # TODO: implement this
        pass

    def _post_process_author_query(self, query: AuthorQuery,
                                   data: PubMedData) -> PubMedData:
        # TODO: implement this
        pass

    def _post_process_author_by_id_query(self, query: AuthorByIDQuery,
                                         data: PubMedData) -> PubMedData:
        # TODO: implement this
        pass

    def _post_process_coauthor_by_id_query(self, query: CoauthorByIDQuery,
                                           data: PubMedData) -> PubMedData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedData) -> Data:
        # TODO: implement this
        pass
