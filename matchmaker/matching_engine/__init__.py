
from matchmaker.query_engine.data_types import InstitutionData, AuthorData
from matchmaker.query_engine.query_types import Institution, PaperSearchQuery, InstitutionSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from typing import Callable, List, Union, TypeVar, Generic

from matchmaker.query_engine.selector_types import  InstitutionDataSelector, AuthorDataSelector
#from matchmaker.query_engine.backends.scopus import ScopusInstitutionSearchQueryEngine
from matchmaker.query_engine.backends import BaseInstitutionSearchQueryEngine, BaseAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseAuthorSearchQueryEngine as BaseMetaAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseInstitutionSearchQueryEngine as BaseMetaInstitutionSearchQueryEngine

class CorrelationFunction:
    def __init__(self, backend) -> None:

        pass
class AbstractMatchingEngine:
    pass

class AbstractAuthorGetter:
    inst_selector: InstitutionDataSelector
    author_selector: AuthorDataSelector
    async def get_institution_data_from_name(self, institution_name: str, inst_selector) -> List[InstitutionData]:
        raise NotImplementedError
    async def get_institution_id_from_data(self, data: List[InstitutionData]) -> str:
        raise NotImplementedError
    async def get_institution_id(self, institution_name:str) -> str:
        return await self.get_institution_id_from_data(await self.get_institution_data_from_name(institution_name, self.inst_selector))
    async def get_associated_authors(self, institution_id: str, author_selector) -> List[AuthorData]:
        raise NotImplementedError
    async def __call__(self, institution_name: str) -> List[AuthorData]:
        return await self.get_associated_authors(await self.get_institution_id(institution_name), self.author_selector)


InstitutionEngine = TypeVar('InstitutionEngine', bound = SlightlyLessAbstractQueryEngine)
AuthorEngine = TypeVar('AuthorEngine', bound = SlightlyLessAbstractQueryEngine)
class AuthorGetter(AbstractAuthorGetter, Generic[AuthorEngine, InstitutionEngine]):
    def __init__(
        self, 
        institution_query_engine: InstitutionEngine, 
        author_query_engine: AuthorEngine,
        choose_institution_callback: Callable[[List[InstitutionData]], str]
    ) -> None:
        self.institution_query_engine = institution_query_engine
        self.author_query_engine = author_query_engine
        self.choose_institution_callback = choose_institution_callback
    async def get_institution_data_from_name(self, institution_name: str, inst_selector) -> List[InstitutionData]:
        institution_query = InstitutionSearchQuery.parse_obj({
            'query':{
                'tag': 'institution',
                'operator': {
                    'tag': 'equal',
                    'value': institution_name
                },
            },
            'selector': inst_selector.dict()
        })
        return await self.institution_query_engine(institution_query)
    async def get_institution_id_from_data(self, data: List[InstitutionData]) -> str:
        if len(data) == 0:
            raise ValueError('Institution not found')
        elif len(data) == 1:
            relevant_institution = data[0]
            return relevant_institution.id
        else:
            return self.choose_institution_callback(data)
    async def get_associated_authors(self, institution_id: str, author_selector) -> List[AuthorData]:
        author_query = AuthorSearchQuery.parse_obj({
            'query':{
                'tag': 'institutionid',
                'operator': {
                    'tag': 'equal',
                    'value': institution_id
                },
            },
            'selector': author_selector.dict()
        })
        return await self.author_query_engine(author_query)
