from matchmaker.query_engine.backends.pubmed import PubmedBackend, PaperSearchQueryEngine
from matchmaker.query_engine.backends.scopus import ScopusBackend, InstitutionSearchQueryEngine
from matchmaker.query_engine.backends.scopus.api import Auth

from matchmaker.query_engine.data_types import AuthorData, PaperData, InstitutionData, BasePaperData
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


def author_query_to_paper_query(query: AuthorSearchQuery, available_fields: AuthorDataSelector) -> PaperSearchQuery:
    #Since author query is a subset of paper query

    new_selector = AuthorDataSelector.generate_subset_selector(query.selector, available_fields)
    new_query = PaperSearchQuery.parse_obj({
        'query': query.query.dict(),
        'selector': {'authors': new_selector.dict()}
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
    async def _query_to_awaitable(self, query: AuthorSearchQuery):
        if query.selector not in self.available_fields:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        paper_query = author_query_to_paper_query(query, self.pubmed_paper_search.available_fields.authors)
        native_query = await self.pubmed_paper_search.get_native_query(paper_query)
        async def make_coroutine() -> List[PaperData]:
            papers = await self.pubmed_paper_search.get_data_from_native_query(paper_query, native_query)
            return papers
        return make_coroutine, native_query.metadata

    async def _post_process(self, query: AuthorSearchQuery, data: List[PaperData]) -> List[AuthorData]:
        print(data[0])
        return data

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