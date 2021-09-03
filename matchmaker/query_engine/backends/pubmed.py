from pydantic import BaseModel
from typing import List, Union

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend


class PubMedPaperSearchQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorSearchQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedPaperDetailsQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorDetailsQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedCoauthorsQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedPaperData(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorData(BaseModel):
    # TODO: implement this
    pass


def paper_from_native(data):
    raise NotImplementedError('TODO')


class PaperSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperSearchQuery,
            List[PaperData], PubMedPaperSearchQuery, List[PubMedPaperData]]):
    def _query_to_native(self, query: PaperSearchQuery) -> PubMedPaperSearchQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedPaperSearchQuery) -> List[PubMedPaperData]:
        # TODO: implement this
        pass

    def _post_process(self, query: PaperSearchQuery, data: List[PubMedPaperData]) -> List[PubMedPaperData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedPaperData]) -> List[PaperData]:
        return [paper_from_native(datum) for datum in data]


class AuthorSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorSearchQuery,
            List[AuthorData], PubMedAuthorSearchQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: AuthorSearchQuery) -> PubMedAuthorSearchQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorSearchQuery) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorSearchQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
        # TODO: implement this
        pass


class PaperDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperDetailsQuery,
            PaperData, PubMedPaperDetailsQuery, PubMedPaperData]):
    def _query_to_native(self, query: PaperDetailsQuery) -> PubMedPaperDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedPaperDetailsQuery) -> PubMedPaperData:
        # TODO: implement this
        pass

    def _post_process(self, query: PaperDetailsQuery, data: PubMedPaperData) -> PubMedPaperData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedPaperData) -> PaperData:
        return paper_from_native(data)


class AuthorDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorDetailsQuery,
            AuthorData, PubMedAuthorDetailsQuery, PubMedAuthorData]):
    def _query_to_native(self, query: AuthorDetailsQuery) -> PubMedAuthorDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorDetailsQuery) -> PubMedAuthorData:
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorDetailsQuery, data: PubMedAuthorData) -> PubMedAuthorData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedAuthorData) -> AuthorData:
        # TODO: implement this
        pass


class CoauthorQueryEngine(
        SlightlyLessAbstractQueryEngine[CoauthorQuery,
            List[AuthorData], PubMedCoauthorsQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: CoauthorQuery) -> PubMedCoauthorsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedCoauthorsQuery) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _post_process(self, query: CoauthorQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
        # TODO: implement this
        pass


class PubMedBackend(Backend):
    def paperSearchEngine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine()

    def authorSearchEngine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine()

    def paperDetailsEngine(self) -> PaperDetailsQueryEngine:
        return PaperDetailsQueryEngine()

    def authorDetailsEngine(self) -> AuthorDetailsQueryEngine:
        return AuthorDetailsQueryEngine()

    def coauthorsEngine(self) -> CoauthorQueryEngine:
        return CoauthorQueryEngine()
