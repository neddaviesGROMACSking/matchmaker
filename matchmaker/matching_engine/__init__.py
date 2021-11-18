
from matchmaker.query_engine.types.data import InstitutionData, AuthorData, PaperData
from matchmaker.query_engine.types.query import Institution, PaperSearchQuery, InstitutionSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from typing import Callable, List, Union, TypeVar, Generic, Tuple

from matchmaker.query_engine.types.selector import  InstitutionDataSelector, AuthorDataSelector
#from matchmaker.query_engine.backends.scopus import ScopusInstitutionSearchQueryEngine
from matchmaker.query_engine.backends import BaseInstitutionSearchQueryEngine, BaseAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseAuthorSearchQueryEngine as BaseMetaAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseInstitutionSearchQueryEngine as BaseMetaInstitutionSearchQueryEngine
import numpy as np
from numpy.typing import ArrayLike
from matchmaker.matching_engine.abstract_to_abstract import calculate_set_similarity
from tabulate import tabulate #type:ignore

AuthorMatrix = ArrayLike


class CorrelationFunction:
    backend: Backend
    def __init__(self, backend) -> None:
        self.backend = backend
        pass
    async def __call__(self, author_data1: List[AuthorData], author_data2: List[AuthorData]) -> AuthorMatrix:
        raise NotImplementedError

class AbstractToAbstractCorrelationFunction(CorrelationFunction):
    def __init__(self, paper_query_engine: SlightlyLessAbstractQueryEngine) -> None:
        self.paper_query_engine = paper_query_engine
    async def __call__(self, author_data1: List[AuthorData], author_data2: List[AuthorData]) -> AuthorMatrix:
        def process_paper_abstracts(paper: PaperData) -> str:
            abstract = paper.abstract
            if isinstance(abstract, list):
                return ' . '.join([text for _, text in abstract])
            else:
                return abstract
        def bin_items(items: List[str], bin_limit: int) -> List[List[str]]:
            binned_items = []
            current_bin_index = 0
            for i in items:
                if current_bin_index >= len(binned_items):
                    binned_items.append([])
                binned_items[current_bin_index].append(i)
                if len(binned_items[current_bin_index]) >= bin_limit:
                    current_bin_index += 1
            return binned_items

        async def get_author_papers(authors: List[AuthorData]) -> List[List[PaperData]]:
            def group_results_by_author_id(author_ids: List[str], results:List[PaperData]) -> List[List[PaperData]]:
                def get_results_matching_author(author_id: str, results: List[PaperData]) -> List[PaperData]:
                    matched_results = []
                    for result in results:
                        relevant_ids = [author.id for author in result.authors]
                        if author_id in relevant_ids:
                            matched_results.append(result)
                    return matched_results
                binned_results = []
                for author_id in author_ids:
                    binned_results.append(get_results_matching_author(author_id, results))
                return binned_results
            authors_ids = [author.id for author in authors]
            binned_authors = bin_items(authors_ids, 25)
            new_results = []
            for id_set in binned_authors:
                query_dict = {
                    'query': {
                        'tag': 'or',
                        'fields_': [{
                            'tag': 'authorid',
                            'operator': {
                                'tag': 'equal',
                                'value': auth_id
                            }
                        } for auth_id in id_set]
                    },
                    'selector': {
                        'paper_id': True,
                        'abstract': True,
                        'authors': {
                            'id': {'scopus_id': True}
                        }
                    }
                }
                new_results += await self.paper_query_engine(PaperSearchQuery.parse_obj(query_dict))
            return group_results_by_author_id(authors_ids, new_results)

        author_matrix = np.zeros((len(author_data1), len(author_data2)))
        author_papers_1 = await get_author_papers(author_data1)
        author_papers_2 = await get_author_papers(author_data2)
        for i, author1 in enumerate(author_data1):
            asso_papers_1 = author_papers_1[i]
            abstract_set1 = [process_paper_abstracts(paper) for paper in asso_papers_1 if paper.abstract is not None]
            for j, author2 in enumerate(author_data2):
                asso_papers_2 = author_papers_2[j]
                abstract_set2 = [process_paper_abstracts(paper) for paper in asso_papers_2 if paper.abstract is not None]      
                author_matrix[i][j] = calculate_set_similarity(abstract_set1, abstract_set2)
        return author_matrix

class ElementCorrelationFunction(CorrelationFunction):
    async def correlate_authors(self, author1: AuthorData, author2: AuthorData) -> float:
        raise NotImplementedError
    async def __call__(self, author_data1: List[AuthorData], author_data2: List[AuthorData]) -> AuthorMatrix:
        author_matrix = np.zeros((len(author_data1), len(author_data2)))
        for i, author1 in enumerate(author_data1):
            for j, author2 in enumerate(author_data2):
                author_matrix[i][j] = await self.correlate_authors(author1, author2)
        return author_matrix


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
        choose_institution_callback: Callable[[List[InstitutionData]], str],
        inst_selector: InstitutionDataSelector,
        author_selector: AuthorDataSelector
    ) -> None:
        self.institution_query_engine = institution_query_engine
        self.author_query_engine = author_query_engine
        self.choose_institution_callback = choose_institution_callback
        self.inst_selector = inst_selector
        self.author_selector = author_selector
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
            return relevant_institution.id.scopus_id
        else:
            return self.choose_institution_callback(data)
    async def get_associated_authors(self, institution_id: str, author_selector) -> List[AuthorData]:
        author_query = AuthorSearchQuery.parse_obj({
            'query':{
                'tag': 'and',
                'fields_': [
                    {
                        'tag': 'institutionid',
                        'operator': {
                            'tag': 'equal',
                            'value': {
                                'scopus_id': institution_id
                            }
                        }
                    },
                    {
                        'tag': 'year',
                        'operator': {
                            'tag': 'range',
                            'lower_bound': '2018',
                            'upper_bound': '2022'
                        }
                    }
                ]
            },
            'selector': author_selector.dict()
        })
        return await self.author_query_engine(author_query)

class AbstractMatchingEngine:
    pass

StackedAuthorMatrix =ArrayLike
MatchMatrix = ArrayLike
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
        return stacked_author_matrix, author_data1, author_data2
    
    async def process_matches(
        self,
        stacked_author_matrix: StackedAuthorMatrix,
        author_data1: List[AuthorData], 
        author_data2: List[AuthorData]
    ) -> List[Tuple[AuthorData,AuthorData,float]]:
        # TODO Are author_datas being duplicated? Investigate
        final_results: List[Tuple[AuthorData,AuthorData,float]] = []
        for i, author1 in enumerate(author_data1):
            for j, author2 in enumerate(author_data2):
                correlation = np.average(stacked_author_matrix[:,i,j])
                final_results.append((author1,author2,correlation))
        return final_results
    
    async def __call__(self, institution_name1: str, institution_name2: str) -> List[Tuple[AuthorData,AuthorData,float]]:
        stacked_mat, author_data1, author_data2 = await self.make_stacked_author_matrix(institution_name1, institution_name2)
        return await self.process_matches(stacked_mat, author_data1, author_data2)


def display_matches(
    matches: List[Tuple[AuthorData,AuthorData,float]]
):
    final_results = []
    for author1, author2, correlation in matches:
        name1 = author1.preferred_name.given_names + ' ' + author1.preferred_name.surname
        name2 = author2.preferred_name.given_names + ' ' + author2.preferred_name.surname
        final_results.append((name1,name2,correlation))
    dtype = [('Author1', '<U32'), ('Author2', '<U32'), ('Match', float)]
    final = np.sort(np.array(final_results, dtype = dtype),order='Match')
    print(tabulate(final, headers=['Author1', 'Author2', 'Match Rating']))
