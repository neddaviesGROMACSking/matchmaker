
from matchmaker.query_engine.types.data import InstitutionData, AuthorData, PaperData
from matchmaker.query_engine.types.query import AuthorSearchQueryInner, Institution, PaperSearchQuery, InstitutionSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from typing import Callable, List, Union, TypeVar, Generic, Tuple

from matchmaker.query_engine.types.selector import  InstitutionDataSelector, AuthorDataSelector, PaperDataSelector
#from matchmaker.query_engine.backends.scopus import ScopusInstitutionSearchQueryEngine
from matchmaker.query_engine.backends import BaseInstitutionSearchQueryEngine, BaseAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseAuthorSearchQueryEngine as BaseMetaAuthorSearchQueryEngine
from matchmaker.query_engine.backends.metas import BaseInstitutionSearchQueryEngine as BaseMetaInstitutionSearchQueryEngine
import numpy as np
from numpy.typing import ArrayLike
from matchmaker.matching_engine.abstract_to_abstract import calculate_set_similarity
from tabulate import tabulate #type:ignore
from functools import reduce
import csv
AuthorMatrix = ArrayLike


class CorrelationFunction:
    backend: Backend
    required_author_fields: AuthorDataSelector
    def __init__(self, backend) -> None:
        self.backend = backend
        pass
    async def __call__(self, author_data1: List[AuthorData], author_data2: List[AuthorData]) -> AuthorMatrix:
        raise NotImplementedError


class AbstractToAbstractCorrelationFunction(CorrelationFunction):
    def __init__(self, paper_query_engine: SlightlyLessAbstractQueryEngine) -> None:
        self.paper_query_engine = paper_query_engine
        self.required_author_fields = AuthorDataSelector.parse_obj({
            'id': {'scopus_id': True}, 
            #'preferred_name': True
        })
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


class AbstractMatchingEngine:
    pass

StackedAuthorMatrix =ArrayLike
MatchMatrix = ArrayLike
AuthorEngine = TypeVar('AuthorEngine', bound = SlightlyLessAbstractQueryEngine)

class MatchingEngine(Generic[AuthorEngine]):
    author_engine: AuthorEngine
    correlation_functions: List[CorrelationFunction]
    author_selector: PaperDataSelector
    def __init__(
        self,
        author_engine: AuthorEngine,
        correlation_functions: List[CorrelationFunction]
    ):
        self.author_engine = author_engine
        self.correlation_functions = correlation_functions
        self.author_selector = reduce(lambda x, y: x | y, [i.required_author_fields for i in correlation_functions])

    async def _make_author_matrix(
        self,
        correlation_func: CorrelationFunction, 
        author_data1: List[AuthorData], 
        author_data2: List[AuthorData]
    ) -> AuthorMatrix:
        return await correlation_func(author_data1, author_data2)

    async def _make_stacked_author_matrix(
        self,
        author_data1: List[AuthorData], 
        author_data2: List[AuthorData]
    ) -> StackedAuthorMatrix:
        stacked_author_matrix = None
        for i, correlation_func in enumerate(self.correlation_functions):
            auth_mat = await self._make_author_matrix(
                correlation_func,
                author_data1,
                author_data2
            )
            if stacked_author_matrix is None:
                stacked_author_matrix = np.zeros([len(self.correlation_functions)]+ list(auth_mat.shape))
            stacked_author_matrix[i] = auth_mat
        return stacked_author_matrix
    
    async def __call__(
        self, 
        author_query1: AuthorSearchQuery, 
        author_query2: AuthorSearchQuery
    ) -> Tuple[StackedAuthorMatrix, List[AuthorData], List[AuthorData]]:
        selector1 = author_query1.selector | self.author_selector
        selector2 = author_query2.selector | self.author_selector
        query1_with_selector = AuthorSearchQuery(
            query = author_query1.query,
            selector = selector1
        )
        query2_with_selector = AuthorSearchQuery(
            query = author_query2.query,
            selector = selector2
        )
        authors_set1 = await self.author_engine(query1_with_selector)
        authors_set2 = await self.author_engine(query2_with_selector)
        stacked_matrix = await self._make_stacked_author_matrix(authors_set1, authors_set2)
        return stacked_matrix, authors_set1, authors_set2


def process_matches(
    stacked_author_matrix: StackedAuthorMatrix,
    author_data1: List[AuthorData], 
    author_data2: List[AuthorData]
) -> List[Tuple[AuthorData,AuthorData,float]]:
    # TODO Are author_datas being duplicated? Investigate
    print(stacked_author_matrix)

    final_results: List[Tuple[AuthorData,AuthorData,float]] = []
    for i, author1 in enumerate(author_data1):
        for j, author2 in enumerate(author_data2):
            correlation = np.average(stacked_author_matrix[:,i,j])
            final_results.append((author1,author2,correlation))
    return final_results

def display_matches(
    matches: List[Tuple[AuthorData,AuthorData,float]]
):
    final_results = []
    for author1, author2, correlation in matches:
        name1 = author1.preferred_name.given_names + ' ' + author1.preferred_name.surname + f' ({author1.paper_count})'
        name2 = author2.preferred_name.given_names + ' ' + author2.preferred_name.surname + f' ({author2.paper_count})'
        final_results.append((name1,name2,correlation))
    dtype = [('Author1', '<U32'), ('Author2', '<U32'), ('Match', float)]
    final = np.sort(np.array(final_results, dtype = dtype),order='Match')
    print(tabulate(final, headers=['Author1', 'Author2', 'Match Rating']))

def save_matches(
    matches: List[Tuple[AuthorData,AuthorData,float]],
    filename: str
):
    final_results = []
    for author1, author2, correlation in matches:
        name1 = author1.preferred_name.given_names + ' ' + author1.preferred_name.surname + f' ({author1.paper_count})'
        name2 = author2.preferred_name.given_names + ' ' + author2.preferred_name.surname + f' ({author2.paper_count})'
        final_results.append((name1,author1.paper_count, name2, author2.paper_count, correlation))
    dtype = [('Author1', '<U32'),('Author1PC', '<U32'), ('Author2', '<U32'), ('Author2PC', '<U32'), ('Match', float)]
    final = np.sort(np.array(final_results, dtype = dtype),order='Match')
    with open(filename, 'w+', newline='') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for i in final:
            filewriter.writerow(i)
       
