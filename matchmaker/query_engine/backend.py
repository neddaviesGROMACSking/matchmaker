from typing import List

from matchmaker.query_engine.types.query import PaperSearchQuery, \
        AuthorSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.types.data import PaperData, AuthorData, InstitutionData
from matchmaker.query_engine.abstract import AbstractQueryEngine

class Backend:
    def paper_search_engine(self) -> AbstractQueryEngine[PaperSearchQuery, List[PaperData]]:
        raise NotImplementedError('Calling method on abstract base class')

    def author_search_engine(self) -> AbstractQueryEngine[AuthorSearchQuery, List[AuthorData]]:
        raise NotImplementedError('Calling method on abstract base class')

    def institution_search_engine(self) -> AbstractQueryEngine[InstitutionSearchQuery, List[InstitutionData]]:
        raise NotImplementedError('Calling method on abstract base class')
