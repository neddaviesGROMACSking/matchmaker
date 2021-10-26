from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend, InstitutionSearchQueryEngine
from matchmaker.query_engine.backends.scopus.api import Auth

from matchmaker.query_engine.data_types import AuthorData, PaperData, InstitutionData
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend
from typing import Optional, Tuple, Callable, Awaitable, Dict, List, Generic, TypeVar, Union, Any
from asyncio import get_running_loop, gather

from dataclasses import dataclass
import pdb
from pybliometrics.scopus.utils.constants import SEARCH_MAX_ENTRIES
#from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError
from matchmaker.query_engine.backends.tools import TagNotFound, execute_callback_on_tag
from pybliometrics.scopus.exception import ScopusQueryError
from copy import deepcopy
NativeData = TypeVar('NativeData')
DictStructure = Dict[str, Union[str, 'ListStructure', 'DictStructure']]
ListStructure = List[Union[str, 'ListStructure', 'DictStructure']]
@dataclass
class BaseNativeQuery(Generic[NativeData], AbstractNativeQuery):
    coroutine_function: Callable[[], Awaitable[NativeData]]
    metadata: Dict[str, int]
    def count_api_calls(self):
        return sum(self.metadata.values())
    def count_api_calls_by_method(self, method: str):
        return self.metadata[method]

async def get_doi_list_from_data(papers: List[PaperData]) -> List[str]:
    return [paper.paper_id.doi for paper in papers if paper.paper_id.doi is not None]

async def get_doi_query_from_list(dois: List[str]) -> PaperSearchQuery:
    query = {
        'tag': 'or',
        'fields_': [
            {
                'tag': 'doi',
                'operator': {
                    'tag': 'equal',
                    'value': i
                }
            } for i in dois
        ]
    }
    return PaperSearchQuery.parse_obj(query)

async def get_dois_remaining(scopus_dois: List[str], pubmed_dois: List[str]) -> List[str]:
    return [doi for doi in scopus_dois if doi not in pubmed_dois]

class PaperSearchQueryEngine(
    SlightlyLessAbstractQueryEngine[PaperSearchQuery, BaseNativeQuery[List[PaperData]], List[PaperData], List[PaperData], List[PaperData]]):
    def __init__(
        self, 
        scopus_paper_search,
        scopus_paper_standard_search,
        pubmed_paper_search,
        complete_search_request_limit = 100
    ) -> None:
        self.scopus_paper_search = scopus_paper_search
        self.scopus_paper_standard_search = scopus_paper_standard_search
        self.pubmed_paper_search = pubmed_paper_search
        self.complete_search_request_limit = complete_search_request_limit
    
    async def _query_to_awaitable(self, query: PaperSearchQuery) -> Tuple[Callable[[], Awaitable[List[PaperData]]], Dict[str, int]]:
        full_native_query = await self.scopus_paper_search.get_native_query(query)
        full_native_request_no = full_native_query.metadata['scopus_search']
        standard_native_query = await self.scopus_paper_standard_search.get_native_query(query) 
        standard_native_request_no = standard_native_query.metadata['scopus_search']
        # For pubmed it's always the same, so this can be a good estimate
        pubmed_native_query = await self.pubmed_paper_search.get_native_query(query)
        metadata = {
            'scopus_search': full_native_request_no + standard_native_request_no,
            **pubmed_native_query.metadata
        }
        async def make_coroutine() -> List[PaperData]:
            # Step 1 - get standard results
            standard_data = await self.scopus_paper_standard_search.get_data_from_native_query(standard_native_query)
            doi_list_scopus = await get_doi_list_from_data(standard_data)
            doi_query_pubmed = await get_doi_query_from_list(doi_list_scopus)
            # Step 2 - get pubmed data from dois
            pubmed_data = await self.pubmed_paper_search(doi_query_pubmed)
            doi_list_pubmed = await get_doi_list_from_data(pubmed_data)
            dois_remaining = await get_dois_remaining(doi_list_scopus, doi_list_pubmed)
            complete_no_requests = len(dois_remaining)//25 +2

            # Step 3 - get estimate for returning to scopus for more info
            #pubmed will do same as always number of requests!
            #But nature of the query depends upon the results of standard_native_data

            if self.complete_search_request_limit < complete_no_requests:
                return pubmed_data
            else:
                def bin_dois(dois: List[str], bin_limit: int = 25) -> List[List[str]]:
                    binned_dois = []
                    current_bin_index = 0
                    for i in dois:
                        if current_bin_index >= len(binned_dois):
                            binned_dois.append([])
                        binned_dois[current_bin_index].append(i)
                        if len(binned_dois[current_bin_index]) >= bin_limit:
                            current_bin_index += 1
                    return binned_dois
                #split doi list into blocks of 25 (25 per request),
                # to reduce url length per length
                binned_dois = bin_dois(dois_remaining)

                async def get_paper_data_from_dois(dois):
                    doi_query_scopus = await get_doi_query_from_list(dois)
                    return await self.scopus_paper_search(doi_query_scopus)
                results = await gather(*list(map(get_paper_data_from_dois, binned_dois)))
                concat_results = []
                for i in results:
                    concat_results += i
                return pubmed_data + concat_results

        return make_coroutine, metadata
    
    async def _query_to_native(self, query: PaperSearchQuery) -> BaseNativeQuery[List[PaperData]]:
        awaitable, metadata = await self._query_to_awaitable(query)
        return BaseNativeQuery(awaitable, metadata)
    
    async def _run_native_query(self, query: BaseNativeQuery[List[PaperData]]) -> List[PaperData]:
        return await query.coroutine_function()

    async def _post_process(self, query: PaperSearchQuery, data: List[PaperData]) -> List[PaperData]:
        return data

    async def _data_from_processed(self, data: List[PaperData]) -> List[PaperData]:
        return data

class AuthorSearchQueryEngine(
    SlightlyLessAbstractQueryEngine[AuthorSearchQuery, BaseNativeQuery[List[AuthorData]], List[AuthorData], List[AuthorData], List[AuthorData]]):
    def __init__(
        self,
        scopus_paper_search,
        scopus_author_search,
        scopus_institution_search
    ) -> None:
        self.max_entries = SEARCH_MAX_ENTRIES
        self.scopus_paper_search = scopus_paper_search
        self.scopus_author_search = scopus_author_search
        self.scopus_institution_search = scopus_institution_search
    
    async def _query_to_awaitable(self, query: AuthorSearchQuery) -> Tuple[Callable[[], Awaitable[List[AuthorData]]], Dict[str, int]]:

        native_paper_query = await self.scopus_paper_search.get_native_query(query)
        native_paper_query_request_no = native_paper_query.metadata['scopus_search']
        print(native_paper_query_request_no)
        try:
            native_author_query = await self.scopus_author_search.get_native_query(query)
        except TagNotFound:
            native_author_query = None
        except ScopusQueryError:
            native_author_query = None
        direct_author_search = native_author_query is not None and native_author_query.metadata['author_search'] < SEARCH_MAX_ENTRIES/25
        if direct_author_search and native_author_query is not None:
            metadata = native_author_query.metadata
            metadata['institution_search'] = 1
        else:
            metadata = native_paper_query.metadata

        async def make_coroutine() -> List[AuthorData]:
            async def get_unique_authors(query: AuthorSearchQuery, papers: List[PaperData]) -> List[AuthorData]:
                async def construct_author_in_query(query: AuthorSearchQuery) -> Callable[[AuthorData], Optional[AuthorData]]:
                    async def get_institutions_from_query(query: AuthorSearchQuery) -> Tuple[List[InstitutionData],List[Tuple[Any, List[InstitutionData]]]]:
                        institutions =[]
                        def store_institution_callback(dict_structure):
                            institutions.append(dict_structure)
                        execute_callback_on_tag(query.dict()['__root__'], 'institution', store_institution_callback)
                        execute_callback_on_tag(query.dict()['__root__'], 'institutionid', store_institution_callback)
                        institution_query_dict = {
                            'tag': 'or',
                            'fields_': institutions
                        }
                        inst_mapper = []
                        all_insts = []
                        for institution in institutions:
                            return_insts = await self.scopus_institution_search(InstitutionSearchQuery.parse_obj(institution))
                            inst_mapper.append((institution, return_insts))
                            all_insts += return_insts
                        return all_insts, inst_mapper


                    query_institutions, inst_mapper = await get_institutions_from_query(query)
                    def author_in_query(author: AuthorData) -> Optional[AuthorData]:
                        def add_institutions_to_author(author: AuthorData, institutions: List[InstitutionData]) -> AuthorData:
                            def get_more_institution_details(insitution: Optional[InstitutionData], institutions: List[InstitutionData]):
                                def get_institution_from_id(id: str, institutions: List[InstitutionData]) -> Optional[InstitutionData]:
                                    for institution in institutions:
                                        if institution.id == id:
                                            return institution
                                    return None
                                if insitution is not None:
                                    inst_id = insitution.id
                                    if inst_id is not None:
                                        return get_institution_from_id(inst_id, institutions)
                                return None
                            new_author = deepcopy(author)
                            inst_current = author.institution_current
                            new_inst_current = get_more_institution_details(inst_current, institutions)
                            
                            if new_inst_current is not None:
                                new_author.institution_current = new_inst_current
                            
                            for i, other_institution in enumerate(author.other_institutions):
                                new_other_institution = get_more_institution_details(other_institution, institutions)
                                if new_other_institution is not None:
                                    new_author.other_institutions[i] = new_other_institution
                            #print(author)
                            #print(new_author)
                            #print()

                            return new_author
                        
                        def author_matches_query(query: AuthorSearchQuery, author: AuthorData) -> bool:
                            def author_matches_query_inner(
                                institution_names: List[Optional[str]], 
                                institution_ids: List[Optional[str]],
                                author_name: Optional[str],
                                author_id: Optional[str]
                            ) -> Callable[[AuthorSearchQuery], bool]:
                                def query_to_term(query) -> bool:
                                    def get_institution_ids_from_mapper(inst_mapper, query):
                                        for i in inst_mapper:
                                            if i[0] == query:
                                                return [j.id for j in i[1]]
                                    def make_string_term(body_string: Optional[str], q_value: str, operator: str) -> bool:
                                        if body_string is None:
                                            return False
                                        else:
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
                                        return make_string_term(author_name, value, operator)
                                    elif query['tag'] == 'authorid':
                                        operator = query['operator']
                                        value = operator['value']
                                        return make_string_term(author_id, value, operator)
                                    elif query['tag'] == 'institution':
                                        operator = query['operator']
                                        value = operator['value']

                                        query_institution_ids = get_institution_ids_from_mapper(inst_mapper, query)
                                        return any([auth_inst_id in query_institution_ids for auth_inst_id in institution_ids])
                                    elif query['tag'] == 'institutionid':
                                        operator = query['operator']
                                        value = operator['value']
                                        query_institution_ids = get_institution_ids_from_mapper(inst_mapper, query)
                                        return any([auth_inst_id in query_institution_ids for auth_inst_id in institution_ids])
                                    elif query['tag'] == 'year':
                                        return True
                                    else:
                                        tag = query['tag']
                                        raise ValueError(f'Unknown tag: {tag}')

                                return query_to_term

                            institutions = author.other_institutions
                            if author.institution_current is not None:
                                institutions.append(author.institution_current)
                            institution_names = [inst.name for inst in institutions]
                            institution_ids = [inst.id for inst in institutions]

                            return author_matches_query_inner(institution_names,institution_ids,author.preferred_name.surname, author.id)(query.dict()['__root__'])

                        new_author = add_institutions_to_author(author, query_institutions)
                        full_query = AuthorSearchQuery.parse_obj({
                            'tag': 'or',
                            'fields_': [query.dict()['__root__']]
                        })
                        match = author_matches_query(full_query, new_author)
                        if match:
                            return new_author
                        else:
                            return None
                    
                    return author_in_query

                author_in_query = await construct_author_in_query(query)

                unique_authors = {}
                for paper in papers:
                    for author in paper.authors:
                        if author.id not in unique_authors:
                            new_author = author_in_query(author)
                            if new_author:
                                unique_authors[new_author.id] = new_author
                return list(unique_authors.values())

            if direct_author_search:
                results = await self.scopus_author_search.get_data_from_native_query(native_author_query)
                new_results = results
            else:
                results = await self.scopus_paper_search.get_data_from_native_query(native_paper_query)
                new_results = await get_unique_authors(query, results)
            return new_results
        return make_coroutine, metadata

    async def _query_to_native(self, query: AuthorSearchQuery) -> BaseNativeQuery[List[AuthorData]]:
        awaitable, metadata = await self._query_to_awaitable(query)
        return BaseNativeQuery(awaitable, metadata)
    
    async def _run_native_query(self, query: BaseNativeQuery[List[AuthorData]]) -> List[AuthorData]:
        return await query.coroutine_function()

    async def _post_process(self, query: AuthorSearchQuery, data: List[AuthorData]) -> List[AuthorData]:
        return data

    async def _data_from_processed(self, data: List[AuthorData]) -> List[AuthorData]:
        return data

class OptimisedScopusBackend(Backend):
    def __init__(
        self, 
        scopus_backend: ScopusBackend, 
        pubmed_backend: PubmedBackend
    ) -> None:
        self.scopus_backend = scopus_backend
        self.pubmed_backend = pubmed_backend
    
    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            self.scopus_backend.paper_search_engine(full_view = True), 
            self.scopus_backend.paper_search_engine(full_view = True),
            self.pubmed_backend.paper_search_engine()
        )

    def author_search_engine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine(
            self.scopus_backend.paper_search_engine(full_view = True),
            self.scopus_backend.author_search_engine(),
            self.scopus_backend.institution_search_engine()
        )
    
    def institution_search_engine(self) -> InstitutionSearchQueryEngine:
        return self.scopus_backend.institution_search_engine()
