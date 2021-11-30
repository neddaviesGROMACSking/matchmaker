from html import unescape
from typing import AsyncIterator, Awaitable, Callable, Dict, Generic, Iterator, List, Tuple, Optional, TypeVar
from matchmaker import query_engine
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.backends.web import (
    WebAuthorSearchQueryEngine,
    WebInstitutionSearchQueryEngine,
    WebPaperSearchQueryEngine,
    NewAsyncClient,
    RateLimiter,
    WebNativeQuery
)
from matchmaker.query_engine.backends import MetadataType
from matchmaker.query_engine.backends.scopus.api import (
    AffiliationSearchQuery,
    AffiliationSearchResult,
    ScopusAuthorSearchQuery,
    ScopusAuthorSearchResult,
    ScopusSearchQuery,
    ScopusSearchResult,
    affiliation_search_on_query,
    author_search_on_query,
    get_affiliation_query_no_requests,
    get_affiliation_query_remaining_in_cache,
    get_author_query_no_requests,
    get_author_query_remaining_in_cache,
    get_scopus_query_no_requests,
    get_scopus_query_remaining_in_cache,
    scopus_search_on_query,
)

from matchmaker.query_engine.backends.tools import (
    execute_callback_on_tag,
    replace_dict_tags,
    get_available_model_tags,
    check_model_tags
)
from matchmaker.query_engine.types.data import AuthorData, InstitutionData, PaperData
from matchmaker.query_engine.types.selector import AuthorDataSelector, InstitutionDataSelector, PaperDataSelector
from matchmaker.query_engine.types.query import (
    AuthorSearchQuery,
    InstitutionSearchQuery,
    PaperSearchQuery,
)

from matchmaker.query_engine.backends.exceptions import QueryNotSupportedError
class NotEnoughRequests(Exception):
    pass

def convert_author_id(dict_structure):
    operator = dict_structure['operator']
    assert dict_structure['tag'] == 'authorid'
    operator_value = operator['value']
    scopus_id = operator_value['scopus_id']
    return {
        'tag': dict_structure['tag'],
        'operator': {
            'tag': operator['tag'],
            'value': scopus_id
        }
    }

def convert_institution_id(dict_structure):
    operator = dict_structure['operator']
    assert dict_structure['tag'] == 'institutionid'
    operator_value = operator['value']
    scopus_id = operator_value['scopus_id']
    return {
        'tag': 'affiliationid',
        'operator': {
            'tag': operator['tag'],
            'value': scopus_id
        }
    }

def convert_paper_id(dict_structure):
    operator = dict_structure['operator']
    assert dict_structure['tag'] == 'id'
    operator_value = operator['value']
    id_searches = []
    for id_type, value in operator_value.items():
        if 'doi' == id_type and value is not None:
            id_searches.append({
                'tag': 'doi',
                'operator': {
                    'tag': operator['tag'],
                    'value': value
                }
            })
        elif 'pubmed_id' == id_type and value is not None:
            id_searches.append({
                'tag': 'pmid',
                'operator': {
                    'tag': operator['tag'],
                    'value': value
                }
            })
        elif 'scopus_id' == id_type and value is not None:
            raise ValueError('Scopus id queries not supported')
        elif value is None:
            pass
        else:
            raise ValueError(f'Unknown id type: {id_type}')
    if len(id_searches) == 0:
        raise ValueError('No ids selected')
    elif len(id_searches) ==1:
        return id_searches[0]
    else:
        return {
            'tag': 'or',
            'fields_': id_searches
        }

def paper_query_to_scopus(query: PaperSearchQuery) -> ScopusSearchQuery:
    query_dict = query.dict()['query']
    new_query_dict = replace_dict_tags(
        query_dict,
        auth = 'author',
        srctitle = 'journal',
        authorkeyword = 'keyword',
        keyword = 'topic',
        affiliation = 'institution',
    )
    new_query_dict = execute_callback_on_tag(new_query_dict, 'authorid', convert_author_id)
    new_query_dict = execute_callback_on_tag(new_query_dict, 'institutionid', convert_institution_id)
    new_query_dict = execute_callback_on_tag(new_query_dict, 'id', convert_paper_id)
    model_tags = get_available_model_tags(ScopusSearchQuery)
    check_model_tags(model_tags, new_query_dict)
    return ScopusSearchQuery.parse_obj(new_query_dict)

def author_query_to_scopus_author(query: AuthorSearchQuery) -> ScopusAuthorSearchQuery:
    def convert_author(dict_structure):
        operator = dict_structure['operator']
        tag = operator['tag']
        author = operator['value']
        names = author.split(' ')
        firsts = ' '.join(names[0:-1])
        last = names[-1]
        if firsts == '':
            new_dict_structure = {
                'tag': 'authlast',
                'operator': operator
            }
        else:
            new_dict_structure = {
                'tag': 'and',
                'fields_': [
                    {
                        'tag': 'authfirst',
                        'operator': {
                            'tag': tag,
                            'value': firsts
                        }
                    },
                    {
                        'tag': 'authlast',
                        'operator': {
                            'tag': tag,
                            'value': last
                        },
                    }
                ]
            }

        return new_dict_structure

    query_dict = query.dict()['query']

    new_query_dict = replace_dict_tags(
        query_dict,
        affiliation = 'institution'
    )
    new_query_dict = execute_callback_on_tag(new_query_dict, 'author', convert_author)
    new_query_dict = execute_callback_on_tag(new_query_dict, 'authorid', convert_author_id)
    new_query_dict = execute_callback_on_tag(new_query_dict, 'institutionid', convert_institution_id)
    model_tags = get_available_model_tags(ScopusAuthorSearchQuery)
    check_model_tags(model_tags, new_query_dict)
    return ScopusAuthorSearchQuery.parse_obj(new_query_dict)

def institution_query_to_affiliation(query: InstitutionSearchQuery) -> AffiliationSearchQuery:
    query_dict = query.dict()['query']
    new_query_dict = replace_dict_tags(
        query_dict,
        affiliation = 'institution'
    )
    new_query_dict = execute_callback_on_tag(new_query_dict, 'institutionid', convert_institution_id)
    model_tags = get_available_model_tags(AffiliationSearchQuery)
    check_model_tags(model_tags, new_query_dict)
    return AffiliationSearchQuery.parse_obj(new_query_dict) 


DataForProcess = TypeVar('DataForProcess')
ProcessedData = TypeVar('ProcessedData')
class ScopusProcessedData(AsyncIterator, Generic[DataForProcess, ProcessedData]):
    _iterator: Iterator[DataForProcess]
    _processor: Callable[[DataForProcess], Awaitable[ProcessedData]]
    def __init__(self, iterator: Iterator[DataForProcess], processing_func: Callable[[DataForProcess], Awaitable[ProcessedData]]) -> None:
        self._iterator = iterator
        self._processor = processing_func
        super().__init__()
    async def __anext__(self):
        try:
            next_item = next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration
        return await self._processor(next_item)
    def __aiter__(self) -> AsyncIterator[DataForProcess]:
        return self

        
    #raise NotImplementedError

class PaperSearchQueryEngine(
        WebPaperSearchQueryEngine[WebNativeQuery[List[ScopusSearchResult]],List[ScopusSearchResult], ScopusProcessedData[ScopusSearchResult, PaperData]]):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(max_requests_per_second = 9), *args, **kwargs):
        self.api_key = api_key
        self.institution_token = institution_token
        self.available_fields = PaperDataSelector.parse_obj({
            'paper_id': {
                'doi': True,
                'pubmed_id': True,
                'scopus_id': True
            },
            'title': True,
            'authors': {
                'preferred_name': {
                    'surname': True,
                    'given_names': True
                },
                'id': {
                    'scopus_id': True
                },
                'other_institutions': {
                    'id': {
                        'scopus_id': True
                    }
                }
            },
            'year': True,
            'source_title': True,
            'source_title_id': True,
            'abstract': True,
            'keywords': True,
            'institutions': {
                'name': True,
                'id': {
                    'scopus_id': True
                },
                'processed': True
            }
        })
        self.complete_fields = self.available_fields
        self.standard_fields = PaperDataSelector.parse_obj({
            'paper_id': {
                'doi': True,
                'pubmed_id': True,
                'scopus_id': True
            },
            'title': True,
            'year': True,
            'source_title': True,
            'source_title_id': True,
            'institutions': {
                'name': True,
                'processed': True
            }
        })
        self.possible_searches = [self.complete_fields, self.standard_fields]
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: PaperSearchQuery, 
        client: NewAsyncClient
    ) -> Tuple[
            Callable[
                [NewAsyncClient], 
                Awaitable[List[ScopusSearchResult]]
            ], 
            Callable[
                [], 
                Awaitable[MetadataType]
            ]
        ]:

        scopus_search_query = paper_query_to_scopus(query)


        if query.selector in self.available_fields:
            if query.selector in self.standard_fields:
                view = 'STANDARD'
            else:
                view = 'COMPLETE'
        else:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)


        async def get_metadata() -> MetadataType:
            cache_remaining: int = await get_scopus_query_remaining_in_cache()
            if cache_remaining > 1:
                no_requests: int = await get_scopus_query_no_requests(scopus_search_query, client, view, self.api_key, self.institution_token)
            else:
                raise NotEnoughRequests()
            cache_remaining: int = await get_scopus_query_remaining_in_cache()
            return {
                'scopus_search': (no_requests, cache_remaining)
            }

        async def get_data(client: NewAsyncClient) -> List[ScopusSearchResult]:
            cache_remaining = await get_scopus_query_remaining_in_cache()
            if cache_remaining > 1:
                no_requests = await get_scopus_query_no_requests(scopus_search_query, client, view, self.api_key, self.institution_token)
            else:
                raise NotEnoughRequests()
            cache_remaining = await get_scopus_query_remaining_in_cache()
            if no_requests > cache_remaining:
                raise NotEnoughRequests()
            
            return await scopus_search_on_query(scopus_search_query, client, view, self.api_key, self.institution_token)
        return get_data, get_metadata
    
    async def _post_process(self, query: PaperSearchQuery, data: List[ScopusSearchResult]) -> ScopusProcessedData[ScopusSearchResult, PaperData]:
        model = PaperData.generate_model_from_selector(query.selector)

        async def process_paper_data(data: ScopusSearchResult) -> PaperData:
            new_paper_dict ={}
            paper_dict = data.dict()
            paper_id = {}
            if query.selector.any_of_fields(
                PaperDataSelector.parse_obj({
                    'paper_id':{
                        'scopus_id': True,
                        'doi': True,
                        'pubmed_id': True
                    }
                })
            ):
                if PaperDataSelector.parse_obj({'paper_id':{'scopus_id': True}}) in query.selector:
                    eid = paper_dict['eid']
                    paper_id['scopus_id'] = eid.split('-')[-1]
                if PaperDataSelector.parse_obj({'paper_id':{'doi':True}}) in query.selector:
                    paper_id['doi'] = paper_dict['doi']
                if PaperDataSelector.parse_obj({'paper_id':{'pubmed_id':True}}) in query.selector:
                    paper_id['pubmed_id'] = paper_dict['pubmed_id']

                new_paper_dict['paper_id'] = paper_id

            if PaperDataSelector(title = True) in query.selector:
                new_paper_dict['title'] = paper_dict['title']
            if PaperDataSelector(abstract = True) in query.selector:
                new_paper_dict['abstract'] = paper_dict['description']
            if PaperDataSelector(source_title = True) in query.selector:
                new_paper_dict['source_title'] = paper_dict['publicationName']
            if PaperDataSelector(source_title_id = True) in query.selector:
                new_paper_dict['source_title_id'] = paper_dict['source_id']
            if PaperDataSelector(cited_by = True) in query.selector:
                new_paper_dict['cited_by'] = paper_dict['citedby_count']
            if PaperDataSelector(keywords = True) in query.selector:
                keywords = paper_dict['authkeywords']
                if keywords is not None:
                    new_paper_dict['keywords'] = keywords.split(' | ')
                else:
                    new_paper_dict['keywords'] = keywords
            if PaperDataSelector(year = True) in query.selector:
                cover_date = paper_dict['coverDate']
                new_paper_dict['year'] = cover_date.split('-')[0]
            
            if query.selector.any_of_fields(PaperDataSelector.parse_obj({
                'authors': {
                    'preferred_name': {
                        'surname': True,
                        'given_names': True
                    },
                    'id': {
                        'scopus_id': True
                    },
                    'other_institutions': {
                        'id': {
                            'scopus_id': True
                        },
                    }
                },
            })):
                surname_selected = PaperDataSelector.parse_obj({
                    'authors':{
                        'preferred_name':{
                            'surname': True
                        }
                    }
                })
                given_names_selected = PaperDataSelector.parse_obj({
                    'authors':{
                        'preferred_name':{
                            'given_names': True
                        }
                    }
                })
                auth_id_selected = PaperDataSelector.parse_obj({
                    'authors':{
                        'id': {
                            'scopus_id': True
                        }
                    }
                })
                other_inst_id_selected = PaperDataSelector.parse_obj({
                    'authors':{
                        'other_institutions':{
                            'id': {
                                'scopus_id': True
                            }
                        }
                    }
                })

                author_names = paper_dict['author_names']

                if author_names is not None:
                    if author_names[0] == '(':
                        author_names = author_names[1:-1].split(';')
                    else:
                        author_names = author_names.split(';')

                    if other_inst_id_selected in query.selector:
                        author_afids = paper_dict['author_afids']
                        if author_afids is not None:
                            author_afids = [i.split('-') for i in author_afids.split(';')]
                    else:
                        author_afids = None
                    if auth_id_selected in query.selector:
                        author_ids = paper_dict['author_ids']
                        if author_ids is not None:
                            author_ids = author_ids.split(';')
                    else:
                        author_ids = None
            
                    new_authors = []
                    for j, author_name in enumerate(author_names):
                        new_author = {}
                        if query.selector.any_of_fields(PaperDataSelector.parse_obj({
                            'authors':{
                                'preferred_name':{
                                    'given_names': True,
                                    'surname': True
                                }
                            }
                        })):
                            new_author_name = {}
                            names = author_name.split(',')
                            if surname_selected in query.selector:
                                new_author_name['surname'] = names[0]
                            if given_names_selected in query.selector:
                                if len(names) > 1:
                                    given_names = names[1]
                                else:
                                    given_names = None
                                new_author_name['given_names'] = given_names
                            new_author['preferred_name'] = new_author_name
                        if auth_id_selected in query.selector:
                            if author_ids is not None and (len(author_names) == len(author_ids)):
                                new_author['id'] = {'scopus_id': author_ids[j]}
                            else:
                                new_author['id'] = None
                        if other_inst_id_selected in query.selector:
                            if author_afids is not None and len(author_names) == len(author_afids):
                                new_author['other_institutions'] = [{'id': {'scopus_id':k}} for k in author_afids[j]]
                            else:
                                new_author['other_institutions'] = []
                        new_authors.append(new_author)
                else:
                    new_authors = []
                new_paper_dict['authors'] = new_authors

            if query.selector.any_of_fields(
                PaperDataSelector.parse_obj({
                    'institutions':{
                        'id': {
                            'scopus_id': True
                        },
                        'name': True,
                        'processed': True
                    }
                })
            ):
                affilname = paper_dict['affilname']
                if affilname is not None:
                    afid = paper_dict['afid']
                    if afid is not None:
                        afids = afid.split(';')
                    else:
                        afids = afid
                    affil_names = unescape(affilname).split(';')
                    affil_cities = unescape(paper_dict['affiliation_city']).split(';')
                    affil_countries = unescape(paper_dict['affiliation_country']).split(';')

                    new_institutions = []
                    for i, affil_name in enumerate(affil_names):
                        new_institution = {}
                        if PaperDataSelector.parse_obj({'institutions': {'id': {'scopus_id': True}}}) in query.selector:
                            if afids is not None and len(affil_names) == len(afids):
                                new_institution['id'] = {'scopus_id': afids[i]}
                            else:
                                new_institution['id'] = None
                        if PaperDataSelector.parse_obj({'institutions': {'processed': True}}) in query.selector:
                            affil_proc = []
                            affil_proc.append((affil_name, 'house'))
                            if len(affil_cities) == len(affil_names):
                                affil_city = affil_cities[i]
                                affil_proc.append((affil_city, 'city'))
                            if len(affil_countries) == len(affil_names):
                                affil_country = affil_countries[i]
                                affil_proc.append((affil_country, 'country'))
                            new_institution['processed'] = affil_proc
                        if PaperDataSelector.parse_obj({'institutions': {'name': True}}) in query.selector:
                            new_institution['name'] = affil_name
                        new_institutions.append(new_institution)
                else:
                    new_institutions = None
                new_paper_dict['institutions'] = new_institutions
            return model.parse_obj(new_paper_dict)
        new_papers = []
        data_iter = iter(data)
        return ScopusProcessedData[ScopusSearchResult, PaperData](data_iter, process_paper_data)



class AuthorSearchQueryEngine(
    WebAuthorSearchQueryEngine[WebNativeQuery[List[ScopusAuthorSearchResult]],List[ScopusAuthorSearchResult], ScopusProcessedData[ScopusAuthorSearchResult, AuthorData]]
):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(max_requests_per_second = 2), *args, **kwargs):
        self.api_key = api_key
        self.institution_token = institution_token
        self.available_fields = AuthorDataSelector.parse_obj({
            'id': {
                'scopus_id': True
            },
            'preferred_name':{
                'surname': True,
                'initials': True,
                'given_names': True,
            },
            'subjects': True,
            'institution_current': {
                'name': True,
                'id': {
                    'scopus_id': True
                },
                'processed': True
            },
            'paper_count': True
        })
        self.possible_searches = [self.available_fields]
           
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: AuthorSearchQuery, 
        client: NewAsyncClient
    ) -> Tuple[
            Callable[
                [NewAsyncClient], 
                Awaitable[List[ScopusAuthorSearchResult]]
            ], 
            Callable[
                [], 
                Awaitable[MetadataType]
            ]
        ]:
        
        if query.selector not in self.available_fields:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        author_search_query = author_query_to_scopus_author(query)

        async def get_metadata() -> MetadataType:
            cache_remaining = await get_author_query_remaining_in_cache()
            if cache_remaining > 1:
                no_requests = await get_author_query_no_requests(author_search_query, client, self.api_key, self.institution_token)
            else:
                raise NotEnoughRequests()
            cache_remaining = await get_author_query_remaining_in_cache()
            metadata: MetadataType = {
                'author_search': (no_requests, cache_remaining)
            }
            return metadata
        async def get_data(client: NewAsyncClient) -> List[ScopusAuthorSearchResult]:
            cache_remaining = await get_author_query_remaining_in_cache()
            if cache_remaining > 1:
                no_requests = await get_author_query_no_requests(author_search_query, client, self.api_key, self.institution_token)
            else:
                raise NotEnoughRequests()
            cache_remaining = await get_author_query_remaining_in_cache()
            if no_requests > cache_remaining:
                raise NotEnoughRequests()
            
            return await author_search_on_query(author_search_query, client, self.api_key, self.institution_token)
        return get_data, get_metadata
    
    async def _post_process(self, query: AuthorSearchQuery, data: List[ScopusAuthorSearchResult]) -> List[AuthorData]:
        new_authors = []
        model = AuthorData.generate_model_from_selector(query.selector)
        for author in data:
            author_dict = author.dict()
            new_author_dict = {}
            if AuthorDataSelector.parse_obj({'id': {'scopus_id': True}}) in query.selector:
                new_author_dict['id'] = {'scopus_id': author_dict['eid'].split('-')[-1]}
            if query.selector.any_of_fields(AuthorDataSelector.parse_obj({
                'preferred_name':{
                    'given_names': True,
                    'surname': True,
                    'initials': True
                }
            })):
                preferred_name = {}
                if AuthorDataSelector.parse_obj({'preferred_name':{'surname': True}}) in query.selector:
                    preferred_name['surname'] = author_dict['surname']
                if AuthorDataSelector.parse_obj({'preferred_name':{'initials': True}}) in query.selector:
                    preferred_name['initials'] = author_dict['initials']
                if AuthorDataSelector.parse_obj({'preferred_name':{'given_names': True}}) in query.selector:
                    preferred_name['given_names'] = author_dict['givenname']
                new_author_dict['preferred_name'] = preferred_name
            
            if AuthorDataSelector(paper_count = True) in query.selector:
                new_author_dict['paper_count'] = int(author_dict['documents'])
            if AuthorDataSelector(subjects = True) in query.selector:
                if author_dict['areas'] != ' ()':
                    subject_list = author_dict['areas'].split('; ')
                    subjects = []
                    for i in subject_list:
                        subject = i[0:4]
                        doc_count = i[6:-1]
                        subjects.append({
                            'name': subject,
                            'paper_count': doc_count
                        })
                else:
                    subjects = []
                new_author_dict['subjects'] = subjects

            if query.selector.any_of_fields(AuthorDataSelector.parse_obj({
                'institution_current': {
                    'name': True,
                    'id': {
                        'scopus_id': True
                    },
                    'processed': True
                }
            })):
                new_institution = {}
                if AuthorDataSelector.parse_obj({'institution_current': {'name': True}}) in query.selector:
                    new_institution['name'] = author_dict['affiliation']
                if AuthorDataSelector.parse_obj({'institution_current': {'id': {'scopus_id': True}}}) in query.selector:
                    new_institution['id'] = {'scopus_id': author_dict['affiliation_id']}
                if AuthorDataSelector.parse_obj({'institution_current': {'processed': True}}) in query.selector:
                    processed = []
                    if author_dict['city'] is not None:
                        processed.append((author_dict['city'], 'city'))
                    if author_dict['country'] is not None:
                        processed.append((author_dict['country'], 'country'))
                        new_institution['processed'] = processed
                new_author_dict['institution_current'] = new_institution
            new_authors.append(model.parse_obj(new_author_dict))
        return new_authors


class InstitutionSearchQueryEngine(
    WebInstitutionSearchQueryEngine[WebNativeQuery[List[AffiliationSearchResult]],List[AffiliationSearchResult], ScopusProcessedData[AffiliationSearchResult, InstitutionData]]
):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(max_requests_per_second = 6), *args, **kwargs):
        self.api_key = api_key
        self.institution_token = institution_token
        self.available_fields = InstitutionDataSelector.parse_obj({
            'id': {
                'scopus_id': True
            },
            'name': True,
            'name_variants': True,
            'paper_count': True,
            'processed': True
        })
        self.possible_searches = [self.available_fields]
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: InstitutionSearchQuery, 
        client: NewAsyncClient
    ) -> Tuple[
            Callable[
                [NewAsyncClient], 
                Awaitable[List[AffiliationSearchResult]]
            ], 
            Callable[
                [], 
                Awaitable[MetadataType]
            ]
        ]:
        if query.selector not in self.available_fields:
            overselected_fields = self.available_fields.get_values_overselected(query.selector)
            raise QueryNotSupportedError(overselected_fields)
        
        affiliation_search_query = institution_query_to_affiliation(query)
        
        async def get_metadata() -> MetadataType:
            cache_remaining = await get_affiliation_query_remaining_in_cache()
            if cache_remaining > 1:
                no_requests = await get_affiliation_query_no_requests(affiliation_search_query, client, self.api_key, self.institution_token)
            else:
                raise NotEnoughRequests()
            cache_remaining = await get_affiliation_query_remaining_in_cache()

            metadata: MetadataType = {
                'affiliation_search': (no_requests, cache_remaining)
            }
            return metadata
        
        async def get_data(client: NewAsyncClient) -> List[AffiliationSearchResult]:
            cache_remaining = await get_affiliation_query_remaining_in_cache()
            if cache_remaining > 1:
                no_requests = await get_affiliation_query_no_requests(affiliation_search_query, client, self.api_key, self.institution_token)
            else:
                raise NotEnoughRequests()
            cache_remaining = await get_affiliation_query_remaining_in_cache()
            if no_requests > cache_remaining:
                raise NotEnoughRequests()
            
            return await affiliation_search_on_query(affiliation_search_query, client, self.api_key, self.institution_token)
        return get_data, get_metadata
    
    async def _post_process(self, query: InstitutionSearchQuery, data: List[AffiliationSearchResult]) -> List[InstitutionData]:
        model = InstitutionData.generate_model_from_selector(query.selector)
        new_papers = []
        for paper in data:
            paper_dict = paper.dict()
            new_paper_dict = {}
            if InstitutionDataSelector.parse_obj({'id':{'scopus_id': True}}) in query.selector:
                new_paper_dict['id'] = {'scopus_id': paper_dict['eid'].split('-')[-1]}
            if InstitutionDataSelector(name = True) in query.selector:
                new_paper_dict['name'] = paper_dict['name']
            if InstitutionDataSelector(name_variants = True) in query.selector:
                new_paper_dict['name_variants'] = [paper_dict['variant']]
            if InstitutionDataSelector(paper_count = True) in query.selector:
                new_paper_dict['paper_count'] = paper_dict['documents']
            if InstitutionDataSelector(processed = True) in query.selector:
                processed = []
                processed.append((paper_dict['name'], 'house'))
                if paper_dict['city'] is not None:
                    processed.append((paper_dict['city'], 'city'))
                if paper_dict['country'] is not None:
                    processed.append((paper_dict['country'], 'country'))
                new_paper_dict['processed'] = processed
            new_paper = model.parse_obj(new_paper_dict)
            new_papers.append(new_paper)
        return new_papers


class ScopusBackend(Backend):
    def __init__(self, api_key: str, institution_token: str):
        self.api_key = api_key
        self.institution_token = institution_token
    
    def paper_search_engine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            api_key = self.api_key, 
            institution_token = self.institution_token
        )

    def author_search_engine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine(
            api_key = self.api_key, 
            institution_token = self.institution_token
        )

    def institution_search_engine(self) -> InstitutionSearchQueryEngine:
        return InstitutionSearchQueryEngine(
            api_key = self.api_key, 
            institution_token = self.institution_token
        )
