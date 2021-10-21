from typing import List, Tuple, Callable, Awaitable, Dict

from matchmaker.query_engine.backends import (
    BaseAuthorSearchQueryEngine,
    BasePaperSearchQueryEngine,
    RateLimiter,
    NewAsyncClient
)
from matchmaker.query_engine.backends.scopus_api_new import (
    AffiliationSearchQuery,
    ScopusAuthorSearchQuery,
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
from matchmaker.query_engine.backends.scopus_utils import create_config
from matchmaker.query_engine.query_types import AuthorSearchQuery, PaperSearchQuery
from aiohttp import ClientSession
from matchmaker.query_engine.data_types import AuthorData, PaperData
from matchmaker.query_engine.backends.tools import replace_dict_tags, replace_dict_tag
from matchmaker.query_engine.backends.scopus_processors import ProcessedScopusSearchResult
from pprint import pprint
from html import unescape
class NotEnoughRequests(Exception):
    pass

def paper_query_to_scopus(query: PaperSearchQuery):
    query_dict = query.dict()['__root__']
    new_query_dict = replace_dict_tags(
        query_dict,
        auth = 'author',
        srctitle = 'journal',
        authorkeyword = 'keyword',
        keyword = 'topic',
        affiliation = 'institution'
    )
    return ScopusSearchQuery.parse_obj(new_query_dict)

def author_query_to_scopus_author(query: AuthorSearchQuery):
    return ScopusAuthorSearchQuery.parse_obj(query.dict()['__root__'])


class PaperSearchQueryEngine(
        BasePaperSearchQueryEngine[List[ScopusSearchResult], List[ProcessedScopusSearchResult]]):
    def __init__(self, api_key:str , institution_token: str, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
        create_config(api_key, institution_token)
        super().__init__(rate_limiter, *args, **kwargs)
    
    async def _query_to_awaitable(self, query: PaperSearchQuery, client: NewAsyncClient) -> Tuple[Callable[[NewAsyncClient], Awaitable[List[ScopusSearchResult]]], Dict[str, int]]:
        scopus_search_query = paper_query_to_scopus(query)
        cache_remaining = await get_scopus_query_remaining_in_cache()
        view = 'COMPLETE'
        if cache_remaining > 1:
            no_requests = await get_scopus_query_no_requests(scopus_search_query, client, view = view)
        else:
            raise NotEnoughRequests()
        cache_remaining = await get_scopus_query_remaining_in_cache()
        if no_requests > cache_remaining:
            raise NotEnoughRequests()
        metadata = {
            'scopus_search': no_requests,
        }
        async def make_coroutine(client: ClientSession) -> List[ScopusSearchResult]:
            return await scopus_search_on_query(scopus_search_query, client, view)
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
                author_afid = author_afids[j]
                other_institutions = [{'id': k} for k in author_afid]
                new_author = {
                    'preferred_name': author_name,
                    'other_institutions': other_institutions,
                    'author_id': author_id
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
            #print(new_paper_dict['other_institutions'])
            new_papers.append(PaperData.parse_obj(new_paper_dict))
            pprint(new_papers[i].dict())
        return new_papers

