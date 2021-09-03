from pydantic import BaseModel
from typing import Generic, List, Type, TypeVar

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.abstract import AbstractQueryEngine

class Backend:
    def paperSearchEngine(self) -> AbstractQueryEngine[PaperSearchQuery, List[PaperData]]:
        raise NotImplementedError('Calling method on abstract base class')

    def authorSearchEngine(self) -> AbstractQueryEngine[AuthorSearchQuery, List[AuthorData]]:
        raise NotImplementedError('Calling method on abstract base class')

    def paperDetailsEngine(self) -> AbstractQueryEngine[PaperDetailsQuery, PaperData]:
        raise NotImplementedError('Calling method on abstract base class')

    def authorDetailsEngine(self) -> AbstractQueryEngine[AuthorDetailsQuery, AuthorData]:
        raise NotImplementedError('Calling method on abstract base class')

    def coauthorsEngine(self) -> AbstractQueryEngine[CoauthorQuery, List[AuthorData]]:
        raise NotImplementedError('Calling method on abstract base class')
