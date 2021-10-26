from html import unescape
from typing import Awaitable, Callable, Dict, List, Tuple
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.backends import (
    BaseAuthorSearchQueryEngine,
    BaseInstitutionSearchQueryEngine,
    BasePaperSearchQueryEngine,
    NewAsyncClient,
    RateLimiter,
)
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
from matchmaker.query_engine.backends.scopus.processors import (
    ProcessedScopusSearchResult,
)
from matchmaker.query_engine.backends.tools import (
    execute_callback_on_tag,
    replace_dict_tags,
    get_available_model_tags,
    check_model_tags
)
from matchmaker.query_engine.data_types import AuthorData, InstitutionData, PaperData
from matchmaker.query_engine.query_types import (
    AuthorSearchQuery,
    InstitutionSearchQuery,
    PaperSearchQuery,
)
import pdb
class NotEnoughRequests(Exception):
    pass

def paper_query_to_scopus(query: PaperSearchQuery) -> ScopusSearchQuery:
    query_dict = query.dict()['__root__']
    new_query_dict = replace_dict_tags(
        query_dict,
        auth = 'author',
        srctitle = 'journal',
        authorkeyword = 'keyword',
        keyword = 'topic',
        affiliation = 'institution'
    )
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
    
    query_dict = query.dict()['__root__']



    new_query_dict = replace_dict_tags(
        query_dict,
        affiliation = 'institution',
        affiliationid = 'institutionid'
    )

    new_query_dict = execute_callback_on_tag(new_query_dict, 'author', convert_author)
    model_tags = get_available_model_tags(ScopusAuthorSearchQuery)
    check_model_tags(model_tags, new_query_dict)
    return ScopusAuthorSearchQuery.parse_obj(new_query_dict)

def institution_query_to_affiliation(query: InstitutionSearchQuery) -> AffiliationSearchQuery:
    query_dict = query.dict()['__root__']
    new_query_dict = replace_dict_tags(
        query_dict,
        affiliation = 'institution',
        affiliationid = 'institutionid'
    )
    model_tags = get_available_model_tags(AffiliationSearchQuery)
    check_model_tags(model_tags, new_query_dict)
    return AffiliationSearchQuery.parse_obj(new_query_dict) 

class PaperSearchQueryEngine(
        BasePaperSearchQueryEngine[List[ScopusSearchResult], List[ProcessedScopusSearchResult]]):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(max_requests_per_second = 9), full_view: bool = True, *args, **kwargs):
        self.api_key = api_key
        self.institution_token = institution_token
        if full_view:
            self.view = 'COMPLETE'
        else:
            self.view = 'STANDARD'
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: PaperSearchQuery, 
        client: NewAsyncClient
    ) -> Tuple[Callable[[NewAsyncClient], Awaitable[List[ScopusSearchResult]]], Dict[str, int]]:
        scopus_search_query = paper_query_to_scopus(query)
        cache_remaining = await get_scopus_query_remaining_in_cache()
        view = self.view
        if cache_remaining > 1:
            no_requests = await get_scopus_query_no_requests(scopus_search_query, client, view, self.api_key, self.institution_token)
        else:
            raise NotEnoughRequests()
        cache_remaining = await get_scopus_query_remaining_in_cache()
        if no_requests > cache_remaining:
            raise NotEnoughRequests()
        metadata = {
            'scopus_search': no_requests,
        }
        async def make_coroutine(client: NewAsyncClient) -> List[ScopusSearchResult]:
            return await scopus_search_on_query(scopus_search_query, client, view, self.api_key, self.institution_token)
        return make_coroutine, metadata
    
    async def _post_process(self, query: PaperSearchQuery, data: List[ScopusSearchResult]) -> List[ProcessedScopusSearchResult]:
        new_papers = []
        for i, paper in enumerate(data):
            new_paper_dict ={}
            paper_dict = paper.dict()
            eid = paper_dict.pop('eid')
            new_paper_dict['scopus_id'] = eid.split('-')[-1]
            new_paper_dict['doi'] = paper_dict['doi']
            new_paper_dict['pubmed_id'] = paper_dict['pubmed_id']
            new_paper_dict['description'] = paper_dict['description']
            new_paper_dict['citedby_count'] = paper_dict['citedby_count']
            new_paper_dict['publicationName'] = paper_dict['publicationName']
            new_paper_dict['title'] = paper_dict['title']
            new_paper_dict['source_id'] = paper_dict['source_id']
            
            afid = paper_dict['afid']
            if afid is not None:
                new_paper_dict['afids'] = afid.split(';')
            else:
                new_paper_dict['afids'] = afid
            

            affilname = paper_dict['affilname']
            if affilname is not None:
                new_paper_dict['affilnames'] = unescape(affilname).split(';')
            else:
                new_paper_dict['affilnames'] = affilname

            if new_paper_dict['affilnames'] is not None:
                affil_cities = unescape(paper_dict['affiliation_city']).split(';')
                affil_countries = unescape(paper_dict['affiliation_country']).split(';')
                affil_procs = []
                for i, a_name in enumerate(new_paper_dict['affilnames']):
                    affil_proc = []
                    affil_city = affil_cities[i]
                    affil_country = affil_countries[i]
                    affil_proc.append((a_name, 'house'))
                    affil_proc.append((affil_city, 'city'))
                    affil_proc.append((affil_country, 'country'))
                    affil_procs.append(affil_proc)
            else:
                affil_procs = None
            
            new_paper_dict['affilprocs'] = affil_procs

            author_names = paper_dict['author_names']
            if author_names[0] == '(':
                author_names = author_names[1:-1]
            author_names = author_names.split(';')
            new_author_names = []
            for author_name in author_names:
                names = author_name.split(',')
                surname = names[0]
                if len(names) > 1:
                    given_names = names[1]
                else:
                    given_names = None
                new_author_name = {
                    'surname': surname,
                    'given_names': given_names
                }
                new_author_names.append(new_author_name)
            new_paper_dict['author_names'] = new_author_names

            author_afids = paper_dict['author_afids']
            if author_afids is not None:
                author_afids = author_afids.split(';')
                author_afids = [i.split('-') for i in author_afids]

            new_paper_dict['author_afids'] = author_afids

            author_ids = paper_dict['author_ids']
            author_ids = author_ids.split(';')
            new_paper_dict['author_ids'] = author_ids

            keywords = paper_dict['authkeywords']
            if keywords is not None:
                new_paper_dict['authkeywords'] = keywords.split(' | ')
            else:
                new_paper_dict['authkeywords'] = keywords
            
            cover_date = paper_dict['coverDate']
            new_paper_dict['year'] = cover_date.split('-')[0]

            new_papers.append(ProcessedScopusSearchResult.parse_obj(new_paper_dict))
        
        return new_papers

    async def _data_from_processed(self, data: List[ProcessedScopusSearchResult]) -> List[PaperData]:
        new_papers = []
        for i, paper in enumerate(data):
            new_paper_dict = {}
            paper_id = {}
            paper_dict = paper.dict()
            if i == 0:
                pass

            paper_id['scopus_id'] = paper_dict['scopus_id']
            paper_id['doi'] = paper_dict['doi']
            paper_id['pubmed_id'] = paper_dict['pubmed_id']
            new_paper_dict['paper_id'] = paper_id

            new_paper_dict['title'] = paper_dict['title']

            author_names = paper_dict['author_names']
            author_ids = paper_dict['author_ids']
            author_afids = paper_dict['author_afids']

            new_authors = []
            for j, author_name in enumerate(author_names):
                author_id = author_ids[j]
                if author_afids is not None:
                    author_afid = author_afids[j]
                    other_institutions = [{'id': k} for k in author_afid]
                else:
                    other_institutions = []
                new_author = {
                    'preferred_name': author_name,
                    'other_institutions': other_institutions,
                    'id': author_id
                }
                new_authors.append(new_author)
            new_paper_dict['authors'] = new_authors

            new_paper_dict['year'] = paper_dict['year']
            new_paper_dict['source_title'] = paper_dict['publicationName']
            new_paper_dict['source_title_id'] = paper_dict['source_id']
            new_paper_dict['abstract'] = paper_dict['description']
            

            affil_names = paper_dict['affilnames']

            if affil_names is not None:
                new_institutions = []
                for m, affil_name in enumerate(affil_names):
                    new_institution = {}
                    new_institution['id'] = paper_dict['afids'][m]
                    new_institution['processed'] = paper_dict['affilprocs'][m]
                    new_institution['name'] = affil_name
                    new_institutions.append(new_institution)
            else:
                new_institutions = None
            new_paper_dict['institutions'] = new_institutions
            new_paper_dict['keywords'] = paper_dict['authkeywords']
            new_paper_dict['cited_by'] = paper_dict['citedby_count']
            new_papers.append(PaperData.parse_obj(new_paper_dict))
        return new_papers


class AuthorSearchQueryEngine(
    BaseAuthorSearchQueryEngine[List[ScopusAuthorSearchResult], List[AuthorData]]
):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(max_requests_per_second = 2), *args, **kwargs):
        self.api_key = api_key
        self.institution_token = institution_token
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: AuthorSearchQuery, 
        client: NewAsyncClient
    ) -> Tuple[Callable[[NewAsyncClient], Awaitable[List[ScopusAuthorSearchResult]]], Dict[str, int]]:
        author_search_query = author_query_to_scopus_author(query)
        cache_remaining = await get_author_query_remaining_in_cache()
        if cache_remaining > 1:
            no_requests = await get_author_query_no_requests(author_search_query, client, self.api_key, self.institution_token)
        else:
            raise NotEnoughRequests()
        cache_remaining = await get_author_query_remaining_in_cache()
        if no_requests > cache_remaining:
            raise NotEnoughRequests()
        metadata = {
            'author_search': no_requests,
        }
        async def make_coroutine(client: NewAsyncClient) -> List[ScopusAuthorSearchResult]:
            return await author_search_on_query(author_search_query, client, self.api_key, self.institution_token)
        return make_coroutine, metadata
    
    async def _post_process(self, query: PaperSearchQuery, data: List[ScopusAuthorSearchResult]) -> List[AuthorData]:
        new_papers = []
        for paper in data:
            paper_dict = paper.dict()
            new_paper_dict = {}
            new_paper_dict['id'] = paper_dict['eid'].split('-')[-1]
            preferred_name = {
                'surname': paper_dict['surname'],
                'initials': paper_dict['initials'],
                'givennames': paper_dict['givenname'],
            }
            new_paper_dict['preferred_name'] = preferred_name
            paper_count = paper_dict['documents']
            new_paper_dict['paper_count'] = int(paper_count)

            if paper_dict['areas'] != ' ()':
                subject_list = paper_dict['areas'].split('; ')
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
            new_paper_dict['subjects'] = subjects
            
            processed = []
            if paper_dict['city'] is not None:
                processed.append((paper_dict['city'], 'city'))
            if paper_dict['country'] is not None:
                processed.append((paper_dict['country'], 'country'))
            new_institution = {
                'name': paper_dict['affiliation'],
                'id': paper_dict['affiliation_id'],
                'processed': processed
            }
            new_paper_dict['institution_current'] = new_institution
            new_papers.append(AuthorData.parse_obj(new_paper_dict))
        return new_papers


    async def _data_from_processed(self, data: List[AuthorData]) -> List[AuthorData]:
        return data




class InstitutionSearchQueryEngine(
    BaseInstitutionSearchQueryEngine[List[AffiliationSearchResult], List[InstitutionData]]
):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(max_requests_per_second = 6), *args, **kwargs):
        self.api_key = api_key
        self.institution_token = institution_token
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: InstitutionSearchQuery, 
        client: NewAsyncClient
    ) -> Tuple[Callable[[NewAsyncClient], Awaitable[List[AffiliationSearchResult]]], Dict[str, int]]:
        affiliation_search_query = institution_query_to_affiliation(query)
        cache_remaining = await get_affiliation_query_remaining_in_cache()
        if cache_remaining > 1:
            no_requests = await get_affiliation_query_no_requests(affiliation_search_query, client, self.api_key, self.institution_token)
        else:
            raise NotEnoughRequests()
        cache_remaining = await get_affiliation_query_remaining_in_cache()
        if no_requests > cache_remaining:
            raise NotEnoughRequests()
        metadata = {
            'affiliation_search': no_requests,
        }
        async def make_coroutine(client: NewAsyncClient) -> List[AffiliationSearchResult]:
            return await affiliation_search_on_query(affiliation_search_query, client, self.api_key, self.institution_token)
        return make_coroutine, metadata
    
    async def _post_process(self, query: PaperSearchQuery, data: List[AffiliationSearchResult]) -> List[InstitutionData]:
        new_papers = []
        for paper in data:
            paper_dict = paper.dict()
            new_paper_dict = {}
            new_paper_dict['id'] = paper_dict['eid'].split('-')[-1]
            new_paper_dict['name'] = paper_dict['name']
            new_paper_dict['name_variants'] = [paper_dict['variant']]
            new_paper_dict['paper_count'] = paper_dict['documents']
            processed = []
            processed.append((paper_dict['name'], 'house'))
            if paper_dict['city'] is not None:
                processed.append((paper_dict['city'], 'city'))
            if paper_dict['country'] is not None:
                processed.append((paper_dict['country'], 'country'))
            new_paper = InstitutionData.parse_obj(new_paper_dict)
            new_papers.append(new_paper)
        return new_papers
    
    async def _data_from_processed(self, data: List[InstitutionData]) -> List[InstitutionData]:
        return data


class ScopusBackend(Backend):
    def __init__(self, api_key: str, institution_token: str):
        self.api_key = api_key
        self.institution_token = institution_token
    
    def paper_search_engine(self, full_view: bool = True) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine(
            api_key = self.api_key, 
            institution_token = self.institution_token,
            full_view = full_view
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
