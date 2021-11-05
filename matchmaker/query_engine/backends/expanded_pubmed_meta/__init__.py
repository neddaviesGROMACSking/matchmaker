from matchmaker.query_engine.backends.pubmed import PubmedBackend, PaperSearchQueryEngine
from matchmaker.query_engine.backends.scopus import ScopusBackend, InstitutionSearchQueryEngine
from matchmaker.query_engine.backends.scopus.api import Auth

from matchmaker.query_engine.data_types import AuthorData, PaperData, InstitutionData
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.selector_types import AuthorDataSelector, PaperDataSelector, PaperDataAllSelected
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend
from typing import Optional, Tuple, Callable, Awaitable, Dict, List, Generic, TypeVar, Union, Any
from asyncio import get_running_loop, gather
from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError, SearchNotPossible
from dataclasses import dataclass
import pdb
from pybliometrics.scopus.utils.constants import SEARCH_MAX_ENTRIES
#from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError
from matchmaker.query_engine.backends.tools import TagNotFound, execute_callback_on_tag
from matchmaker.query_engine.backends.metas import BaseAuthorSearchQueryEngine
from pybliometrics.scopus.exception import ScopusQueryError
from copy import deepcopy


def author_query_to_paper_query(query: AuthorSearchQuery, available_fields: AuthorDataSelector, required_fields: AuthorDataSelector) -> PaperSearchQuery:
    #Since author query is a subset of paper query
    new_selector = AuthorDataSelector.generate_subset_selector(query.selector, available_fields)
    new_selector = AuthorDataSelector.generate_superset_selector(new_selector, required_fields)
    new_query = PaperSearchQuery.parse_obj({
        'query': query.query.dict(),
        'selector': {
            'paper_id': {
                'doi': True,
                'pubmed_id': True
            },
            'authors': new_selector.dict()}
    })
    return new_query


class AuthorSearchQueryEngine(
    BaseAuthorSearchQueryEngine[List[PaperData]]
):
    def __init__(
        self,
        pubmed_paper_search
    ) -> None:
        self.pubmed_paper_search = pubmed_paper_search
        self.available_fields = AuthorDataSelector.parse_obj({
            'preferred_name': True,
            'institution_current': {
                'name': True,
                'processed': True
            },
            'paper_count': True,
            'paper_ids': {
                'pubmed_id': True,
                'doi': True
            },
        })

        self.required_fields = AuthorDataSelector.parse_obj({
            'preferred_name': {
                'surname': True,
                'given_names': True
            },
            'institution_current': {
                'name': True,
                'processed': True
            },
        })
    
    async def _query_to_awaitable(self, query: AuthorSearchQuery):
        if query.selector not in self.available_fields:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        paper_query = author_query_to_paper_query(query, self.pubmed_paper_search.available_fields.authors, self.required_fields)
        native_query = await self.pubmed_paper_search.get_native_query(paper_query)
        async def make_coroutine() -> List[PaperData]:
            papers = await self.pubmed_paper_search.get_data_from_native_query(paper_query, native_query)
            return papers
        return make_coroutine, native_query.metadata

    async def _post_process(self, query: AuthorSearchQuery, data: List[PaperData]) -> List[AuthorData]:
                
        def query_to_func(body_institution: str, body_author: str):
            def query_to_term(query):
                def make_string_term(body_string, q_value, operator):
                    if operator == 'in':
                        return q_value.lower() in body_string.lower()
                    else:
                        return (
                                q_value.lower() in body_string.lower().split(' ')
                            ) or (
                                body_string.lower() in q_value.lower().split(' ')
                            )
                
                if query['tag'] == 'and':
                    fields = query['fields_']
                    return all([query_to_term(field) for field in fields])
                elif query['tag'] == 'or':
                    fields = query['fields_']
                    return any([query_to_term(field) for field in fields])
                elif query['tag'] == 'author':
                    operator = query['operator']
                    value = operator['value']
                    return make_string_term(body_author, value, operator)
                elif query['tag'] == 'institution':
                    operator = query['operator']
                    value = operator['value']
                    return make_string_term(body_institution, value, operator)
                else:
                    raise ValueError('Unknown tag')

            return query_to_term


        def authors_match(author1: AuthorData, author2: AuthorData):
            def institution_matches(inst1: Optional[List[Tuple[str, str]]], inst2: Optional[List[Tuple[str, str]]]):
                match_count = 0
                if inst1 is None or inst2 is None:
                    if inst2 == inst1:
                        return True
                    else:
                        return False
                for part in inst1:
                    if part[1] == 'postcode':
                        #Extract postcodes from other half
                        postcodes2 = [i[0] for i in inst2 if i[1] == 'postcode']
                        #If other half has a postcode, it must match
                        if len(postcodes2)>0:
                            if part[0] in postcodes2:
                                return True
                            else:
                                return False
                    if part[1] == 'house':
                        #Extract houses from other half
                        houses2 = [i[0] for i in inst2 if i[1] == 'house']
                        #If other half has a house, it must match
                        if len(houses2)>0:
                            for house2 in houses2:
                                if part[0] in house2 or house2 in part[0]:
                                    return True
                                else:
                                    return False
                    if part in inst2:
                        match_count += 1
                if match_count >= 4:
                    return True
                else:
                    return False

            proc_institution1 = author1.institution_current.processed
            proc_institution2 = author2.institution_current.processed
            if author1 == author2:
                return True
            elif institution_matches(proc_institution1, proc_institution2):
                return True
            else:
                return False
        def group_by_location(filtered_authors: List[AuthorData]):
            final_list = []
            for i in filtered_authors:
                match_authors = []
                for j in filtered_authors:
                    if authors_match(i,j) and j not in match_authors:
                        match_authors.append(j)
                if match_authors not in final_list:
                    final_list.append(match_authors)
            return final_list
        
        def pick_largest_from_group(location_groups: List[List[AuthorData]]):
            finals = []
            for location_group in location_groups:
                lens = [len(str(i)) for i in location_group]
                group_index = lens.index(max(lens))
                location = location_group[group_index]
                if location not in finals:
                    finals.append(location)
            return finals

        model = AuthorData.generate_model_from_selector(query.selector)


        combined_authors = []
        for result in data:
            combined_authors += result.authors

        query_dict = query.dict()['query']

        filtered_authors = []
        for author in combined_authors:
            if author.preferred_name.surname is None:
                surname_is_present = False
            else:
                surname_is_present = query_to_func(author.institution_current.name, author.preferred_name.surname)(query_dict)
            if author.preferred_name.given_names is None:
                given_is_present = True
            else:
                given_is_present = query_to_func(author.institution_current.name, author.preferred_name.given_names)(query_dict)
            is_present = surname_is_present and given_is_present
            if is_present and author not in filtered_authors:
                filtered_authors.append(author)

        location_groups = group_by_location(filtered_authors)
        finals = pick_largest_from_group(location_groups)

        new_data = []
        for author1 in finals:
            associated_with_author = []
            paper_ids = []
            for paper in data:
                author_list = paper.authors
                for author2 in author_list:
                    if authors_match(author1, author2) and paper not in associated_with_author:
                        associated_with_author.append(paper)
                        paper_ids.append(paper.paper_id)
            paper_count = len(paper_ids)
            #TODO Fix given names not appearing
            new_data.append(model.parse_obj({
                **author1.dict(),
                'paper_count': paper_count,
                'paper_ids': paper_ids
            }))
 
        return new_data





class ExpandedPubmedMeta(Backend):
    def __init__(
        self,
        pubmed_backend: PubmedBackend
    ) -> None:
        self.pubmed_backend = pubmed_backend

    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return self.pubmed_backend.paper_search_engine()
    
    def author_search_engine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine(
            self.pubmed_backend.paper_search_engine()
        )

    def institution_search_engine(self) -> None:
        raise NotImplementedError