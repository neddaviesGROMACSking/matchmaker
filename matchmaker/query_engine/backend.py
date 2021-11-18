from typing import List

from matchmaker.query_engine.types.query import PaperSearchQuery, \
        AuthorSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.types.data import PaperData, AuthorData, InstitutionData
from matchmaker.query_engine.abstract import AbstractQueryEngine

class Backend:
    def PaperSearchEngine(self) -> AbstractQueryEngine[PaperSearchQuery, List[PaperData]]:
        raise NotImplementedError('Calling method on abstract base class')

    def AuthorSearchEngine(self) -> AbstractQueryEngine[AuthorSearchQuery, List[AuthorData]]:
        raise NotImplementedError('Calling method on abstract base class')

    def InstitutionSearchEngine(self) -> AbstractQueryEngine[InstitutionSearchQuery, List[InstitutionData]]:
        raise NotImplementedError('Calling method on abstract base class')
