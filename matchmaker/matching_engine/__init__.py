
from matchmaker.query_engine.data_types import InstitutionData, AuthorData
from matchmaker.query_engine.query_types import Institution, PaperSearchQuery, InstitutionSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from typing import Callable, List, Union, TypeVar, Generic, Tuple

from matchmaker.query_engine.selector_types import  InstitutionDataSelector, AuthorDataSelector
#from matchmaker.query_engine.backends.scopus import ScopusInstitutionSearchQueryEngine
from matchmaker.query_engine.backends import BaseInstitutionSearchQueryEngine, BaseAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseAuthorSearchQueryEngine as BaseMetaAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseInstitutionSearchQueryEngine as BaseMetaInstitutionSearchQueryEngine
import numpy as np

AuthorMatrix = object

class CorrelationFunction:
    backend: Backend
    def __init__(self, backend) -> None:
        pass
    async def __call__(self, author_data1: List[AuthorData], author_data2: List[AuthorData]) -> AuthorMatrix:
        raise NotImplementedError


class ElementCorrelationFunction(CorrelationFunction):
    async def correlate_authors(self, author1: AuthorData, author2: AuthorData):
        raise NotImplementedError
    async def __call__(self, author_data1: List[AuthorData], author_data2: List[AuthorData]) -> AuthorMatrix:
        author_matrix = np.zeros((len(author_data1), len(author_data2)))
        for i, author1 in enumerate(author_data1):
            for j, author2 in enumerate(author_data2):
                author_matrix[i][j] = await self.correlate_authors(author1, author2)
        return author_matrix




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


StackedAuthorMatrix = object
MatchMatrix = object
class MatchingEngine:
    author_matrix: AuthorMatrix
    def __init__(
        self, 
        author_getter: AuthorGetter,
        correlation_functions: List[CorrelationFunction]) -> None:
        self.author_getter = author_getter
        self.correlation_functions = correlation_functions
    
    async def get_authors_from_institution_names(
        self,
        institution_name1: str, 
        institution_name2: str
    ) -> Tuple[List[AuthorData], List[AuthorData]]:
        author_data1 = await self.author_getter(institution_name1)
        author_data2 = await self.author_getter(institution_name2)
        return author_data1, author_data2

    async def make_author_matrix(
        self,
        correlation_func: CorrelationFunction, 
        author_data1: List[AuthorData], 
        author_data2: List[AuthorData]
    ) -> AuthorMatrix:
        return await correlation_func(author_data1, author_data2)

    async def make_stacked_author_matrix(
        self,
        institution_name1: str, 
        institution_name2: str
    ):
        author_data1, author_data2 = await self.get_authors_from_institution_names(
            institution_name1,
            institution_name2
        )
        stacked_author_matrix = None
        for i, correlation_func in enumerate(self.correlation_functions):
            auth_mat = await self.make_author_matrix(
                correlation_func,
                author_data1,
                author_data2
            )
            if stacked_author_matrix is None:
                stacked_author_matrix = np.zeros([len(self.correlation_functions)]+ list(auth_mat.shape))
            stacked_author_matrix[i] = auth_mat
        return stacked_author_matrix
    
    async def process_matches(
        self,
        stacked_author_matrix: StackedAuthorMatrix
    ) -> MatchMatrix:
        return stacked_author_matrix
    
    async def __call__(self, institution_name1: str, institution_name2: str) -> object:
        stacked_mat = await self.make_stacked_author_matrix(institution_name1, institution_name2)
        return await self.process_matches(stacked_mat)
