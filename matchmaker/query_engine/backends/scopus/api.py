from typing import Annotated, List, Literal, Optional, Union

from aiohttp import ClientSession
from matchmaker.query_engine.backends.scopus.constants import Allowance, Length
from matchmaker.query_engine.backends.scopus.quota_cache import (
    get_remaining_in_cache,
    store_quota_in_cache,
)
from matchmaker.query_engine.backends.scopus.results_cache import (
    store_no_results,
    get_no_results,
)
from matchmaker.query_engine.backends.scopus.utils import create_config
from matchmaker.query_engine.types.query import (
    Abstract,
    And,
    AuthorID,
    Keyword,
    Or,
    StringPredicate,
    Title,
    Year,
)
from pybliometrics.scopus import AffiliationSearch, AuthorSearch, ScopusSearch
from pydantic import BaseModel, Field

def query_to_term(query):
    def make_year_term(start_year: Optional[int] = None, end_year: Optional[int] = None):
        if start_year is None and end_year is None:
            raise ValueError('No year provided')
        elif start_year is None:
            return (f'(PUBYEAR < {str(end_year)})')
        elif end_year is None:
            return (f'(PUBYEAR > {str(start_year)})')
        elif start_year == end_year:
            return (f'(PUBYEAR = {str(start_year)})')
        elif start_year < end_year:
            return (f'(PUBYEAR < {str(end_year)} AND PUBYEAR > {str(start_year)})')
        else:
            raise ValueError('Invalid range')

    def make_string_term(string, value, operator):
        if operator == 'in':
            return f'{string}({value}*)'
        else:
            return f'{string}({value})'
    
    if query['tag'] == 'and':
        fields = query['fields_']
        return '('+' AND '.join([query_to_term(field) for field in fields])+')'
    elif query['tag'] == 'or':
        fields = query['fields_']
        return '('+' OR '.join([query_to_term(field) for field in fields])+')'
    elif query['tag'] == 'pmid':
        operator = query['operator']
        value = operator['value']
        return make_string_term('PMID', value, operator)
    elif query['tag'] == 'doi':
        operator = query['operator']
        value = operator['value']
        return make_string_term('DOI', value, operator)
    elif query['tag'] == 'title':
        operator = query['operator']
        value = operator['value']
        return make_string_term('TITLE', value, operator)
    elif query['tag'] == 'authorid':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AU-ID', value, operator)
    elif query['tag'] == 'auth':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AUTH', value, operator)
    elif query['tag'] == 'srctitle':
        operator = query['operator']
        value = operator['value']
        return make_string_term('SRCTITLE', value, operator)
    elif query['tag'] == 'publisher':
        operator = query['operator']
        value = operator['value']
        return make_string_term('PUBLISHER', value, operator)
    elif query['tag'] == 'abstract':
        operator = query['operator']
        value = operator['value']
        return make_string_term('ABS', value, operator)
    elif query['tag'] == 'affiliationid':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AF-ID', value, operator)
    elif query['tag'] == 'affiliation':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AFFIL', value, operator)
    elif query['tag'] == 'keyword':
        operator = query['operator']
        value = operator['value']
        return make_string_term('KEY', value, operator)
    elif query['tag'] == 'authorkeyword':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AUTHKEY', value, operator)
    elif query['tag'] == 'area':
        operator = query['operator']
        value = operator['value']
        return make_string_term('SUBJAREA', value, operator)
    elif query['tag'] == 'authfirst':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AUTHFIRST', value, operator)
    elif query['tag'] == 'authlast':
        operator = query['operator']
        value = operator['value']
        return make_string_term('AUTHLASTNAME', value, operator)
    elif query['tag'] == 'year':
        operator = query['operator']
        if operator['tag'] =='equal':
            value = operator['value']
            return make_year_term(value,value)
        elif operator['tag'] == 'lt':
            value = operator['value']
            return make_year_term(end_year=value)
        elif operator['tag'] == 'gt':
            value = operator['value']
            return make_year_term(start_year=value)
        elif operator['tag'] == 'range':
            lower_bound = operator['lower_bound']
            upper_bound = operator['upper_bound']
            return make_year_term(lower_bound,upper_bound)
        else:
            raise ValueError('Unknown tag')
    else:
        raise ValueError('Unknown tag')



and_int = And['ScopusSearchQuery']
or_int = Or['ScopusSearchQuery']

class Pmid(BaseModel):
    tag: Literal['pmid'] = 'pmid'
    operator: StringPredicate

class Doi(BaseModel):
    tag: Literal['doi'] = 'doi'
    operator: StringPredicate

class Area(BaseModel):
    tag: Literal['area'] = 'area'
    operator: StringPredicate

class AffiliationID(BaseModel):
    tag: Literal['affiliationid'] = 'affiliationid'
    operator: StringPredicate

class ScopusAuthorID(BaseModel):
    tag: Literal['authorid'] = 'authorid'
    operator: StringPredicate

class Affiliation(BaseModel):
    tag: Literal['affiliation'] = 'affiliation'
    operator: StringPredicate

class AuthorKeyword(BaseModel):
    tag: Literal['authorkeyword'] = 'authorkeyword'
    operator: StringPredicate

class Auth(BaseModel):
    tag: Literal['auth'] = 'auth'
    operator: StringPredicate

class SrcTitle(BaseModel):
    tag: Literal['srctitle'] = 'srctitle'
    operator: StringPredicate

class Publisher(BaseModel):
    tag: Literal['publisher'] = 'publisher'
    operator: StringPredicate

class ScopusSearchQuery(BaseModel):
    __root__: Annotated[ 
    Union[
        and_int, 
        or_int, 
        Pmid, 
        Doi, 
        Title, 
        ScopusAuthorID,
        Auth,
        SrcTitle,
        Publisher,
        Abstract,
        AffiliationID,
        Affiliation,
        Keyword,
        AuthorKeyword,
        Area,
        Year
    ],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()


class ScopusSearchResult(BaseModel):
    eid: str
    doi: Optional[str]
    pii: Optional[str]
    pubmed_id: Optional[str]
    title: Optional[str]
    subtype: Optional[str]
    subtypeDescription: Optional[str]
    creator: Optional[str]
    afid: Optional[str]
    affilname: Optional[str]
    affiliation_city: Optional[str]
    affiliation_country: Optional[str]
    author_count: Optional[str]
    author_names: Optional[str]
    author_ids: Optional[str]
    author_afids: Optional[str]
    coverDate: Optional[str]
    coverDisplayDate: Optional[str]
    publicationName: Optional[str]
    issn: Optional[str]
    source_id: Optional[str]
    eIssn: Optional[str]
    aggregationType: Optional[str]
    volume: Optional[str]
    issueIdentifier: Optional[str]
    article_number: Optional[str]
    pageRange: Optional[str]
    description: Optional[str]
    authkeywords: Optional[str]
    citedby_count: Optional[str]
    openaccess: Optional[str]
    fund_acr: Optional[str]
    fund_no: Optional[str]
    fund_sponsor: Optional[str]


class ScopusAuthorSearchResult(BaseModel):
    eid: str
    surname: Optional[str]
    initials: Optional[str]
    givenname: Optional[str]
    affiliation: Optional[str]
    documents: int
    affiliation_id: Optional[str]
    city: Optional[str]
    country: Optional[str]
    areas: Optional[str]

class AuthorFirst(BaseModel):
    tag: Literal['authfirst'] = 'authfirst'
    operator: StringPredicate

class AuthorLast(BaseModel):
    tag: Literal['authlast'] = 'authlast'
    operator: StringPredicate

and_int = And['ScopusAuthorSearchQuery']
or_int = Or['ScopusAuthorSearchQuery']

class ScopusAuthorSearchQuery(BaseModel):
    __root__: Annotated[ 
    Union[
        and_int, 
        or_int, 
        AffiliationID,
        Affiliation,
        ScopusAuthorID,
        AuthorFirst,
        AuthorLast,
        Area,
    ],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()


class AffiliationSearchResult(BaseModel):
    eid: str
    name: Optional[str]
    variant: Optional[str]
    documents: int
    city: Optional[str]
    country: Optional[str]
    parent: Optional[str]

and_int = And['AffiliationSearchQuery']
or_int = Or['AffiliationSearchQuery']

class AffiliationSearchQuery(BaseModel):
    __root__: Annotated[ 
    Union[
        and_int, 
        or_int, 
        AffiliationID,
        Affiliation,
    ],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()

async def scopus_search_on_query(
    query: ScopusSearchQuery,
    client: ClientSession,
    view: str,
    api_key: str,
    institution_token: str
) -> List[ScopusSearchResult]:
    create_config(api_key, institution_token)
    term = query_to_term(query.dict()['__root__'])
    scopus_results = ScopusSearch(term, view = view, verbose = True)
    store_quota_in_cache(scopus_results)
    store_no_results(term, scopus_results)
    paper_results = scopus_results.results
    new_results =[]
    if paper_results is not None:
        for result in paper_results:
            dict_result = result._asdict()
            new_results.append(ScopusSearchResult.parse_obj(dict_result))
        
    return new_results

async def get_scopus_query_no_results(
    query: ScopusSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> int:
    # Note: View not required here, because number of results is independent of view
    create_config(api_key, institution_token)
    term = query_to_term(query.dict()['__root__'])

    no_results = get_no_results('ScopusSearch', term)
    if no_results is None:
        request_search = ScopusSearch(term, download = False)
        store_quota_in_cache(request_search)

        store_no_results(term, request_search)
        no_results = get_no_results('ScopusSearch', term)
        if no_results is None:
            raise RuntimeError
    return no_results

async def get_scopus_query_no_requests(
    query: ScopusSearchQuery,
    client: ClientSession,
    view: str,
    api_key: str,
    institution_token: str
) -> int:
    no_results = await get_scopus_query_no_results(query, client, api_key, institution_token)

    if view == 'COMPLETE':
        return no_results//Length.SCOPUS_COMPLETE_LENGTH +2
    else:
        return no_results//Length.SCOPUS_STANDARD_LENGTH +2

async def get_scopus_query_remaining_in_cache() -> int:
    try:
        return get_remaining_in_cache('ScopusSearch')
    except TypeError:
        return Allowance.SCOPUS_START_ALLOWANCE




async def author_search_on_query(
    query: ScopusAuthorSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> List[ScopusAuthorSearchResult]:
    create_config(api_key, institution_token)
    term = query_to_term(query.dict()['__root__'])
    author_results = AuthorSearch(term, verbose = True)
    store_quota_in_cache(author_results)
    store_no_results(term, author_results)
    authors = author_results.authors
    new_authors =[]
    if authors is not None:
        for author in authors:
            dict_result = author._asdict()
            new_authors.append(ScopusAuthorSearchResult.parse_obj(dict_result))
    return new_authors

async def get_author_query_no_results(
    query: ScopusAuthorSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> int:
    create_config(api_key, institution_token)
    term = query_to_term(query.dict()['__root__'])
    no_results = get_no_results('AuthorSearch', term)
    if no_results is None:
        request_search = AuthorSearch(term, download = False)
        store_quota_in_cache(request_search)
        store_no_results(term, request_search)
        no_results = get_no_results('AuthorSearch', term)
        if no_results is None:
            raise RuntimeError
    return no_results

async def get_author_query_no_requests(
    query: ScopusAuthorSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> int:
    no_results = await get_author_query_no_results(query, client, api_key, institution_token)
    return no_results//Length.AUTHOR_LENGTH +2

async def get_author_query_remaining_in_cache() -> int:
    try:
        return get_remaining_in_cache('AuthorSearch')
    except TypeError:
        return Allowance.AUTH_START_ALLOWANCE


async def affiliation_search_on_query(
    query: AffiliationSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> List[AffiliationSearchResult]:
    create_config(api_key, institution_token)
    term = query_to_term(query.dict()['__root__'])
    affil_results = AffiliationSearch(term, verbose = True)
    store_quota_in_cache(affil_results)
    store_no_results(term, affil_results)
    affiliations = affil_results.affiliations
    new_affiliations =[]
    if affiliations is not None:
        for affiliation in affiliations:
            dict_result = affiliation._asdict()
            new_affiliations.append(AffiliationSearchResult.parse_obj(dict_result))
    return new_affiliations

async def get_affiliation_query_no_results(
    query: AffiliationSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> int:
    create_config(api_key, institution_token)
    term = query_to_term(query.dict()['__root__'])

    no_results = get_no_results('AffiliationSearch', term)
    if no_results is None:
        request_search = AffiliationSearch(term, download = False)
        store_quota_in_cache(request_search)
        store_no_results(term, request_search)
        no_results = get_no_results('AffiliationSearch', term)
        if no_results is None:
            raise RuntimeError
    return no_results

async def get_affiliation_query_no_requests(
    query: AffiliationSearchQuery,
    client: ClientSession,
    api_key: str,
    institution_token: str
) -> int:
    no_results = await get_affiliation_query_no_results(
        query,
        client,
        api_key,
        institution_token
    ) 
    return no_results//Length.AFFIL_LENGTH +2

async def get_affiliation_query_remaining_in_cache() -> int:
    try:
        return get_remaining_in_cache('AffiliationSearch')
    except TypeError:
        return Allowance.AFFIL_START_ALLOWANCE

