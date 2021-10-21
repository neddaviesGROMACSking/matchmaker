from pydantic import BaseModel, Field
from typing import Optional, List, Any, Union, Literal, Annotated
from matchmaker.query_engine.query_types import And, Or, Title,  Abstract, Keyword, Year, StringPredicate, AuthorID
from pybliometrics.scopus import ScopusSearch, AffiliationSearch, AuthorSearch
from matchmaker.query_engine.backends.scopus_quota_cache import store_quota_in_cache, get_remaining_in_cache
from matchmaker.query_engine.backends.scopus_constants import Length, Allowance
from aiohttp import ClientSession
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
        AuthorID,
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


class AuthorSearchResult(BaseModel):
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
        AuthorID,
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
    view: Union[Literal['COMPLETE'], Literal['STANDARD']] = 'COMPLETE'
) -> List[ScopusSearchResult]:
    term = query_to_term(query.dict()['__root__'])
    scopus_results = ScopusSearch(term, view = view, verbose = True)
    store_quota_in_cache(scopus_results)
    paper_results = scopus_results.results
    new_results =[]
    if paper_results is not None:
        for result in paper_results:
            dict_result = result._asdict()
            new_results.append(ScopusSearchResult.parse_obj(dict_result))
        
    return new_results

async def get_scopus_query_no_requests(
    query: ScopusSearchQuery,
    client: ClientSession,
    view: Union[Literal['COMPLETE'], Literal['STANDARD']] = 'COMPLETE'
) -> int:
    term = query_to_term(query.dict()['__root__'])
    request_search = ScopusSearch(term, download = False, view = view)
    store_quota_in_cache(request_search)
    if view == 'COMPLETE':
        return request_search.get_results_size()//Length.SCOPUS_COMPLETE_LENGTH +2
    else:
        return request_search.get_results_size()//Length.SCOPUS_STANDARD_LENGTH +2

async def get_scopus_query_remaining_in_cache() -> int:
    try:
        return get_remaining_in_cache('ScopusSearch')
    except TypeError:
        return Allowance.SCOPUS_START_ALLOWANCE

async def author_search_on_query(
    query: ScopusAuthorSearchQuery,
    client: ClientSession,
) -> List[AuthorSearchResult]:
    term = query_to_term(query.dict()['__root__'])
    author_results = AuthorSearch(term, verbose = True)
    store_quota_in_cache(author_results)
    authors = author_results.authors
    new_authors =[]
    if authors is not None:
        for author in authors:
            dict_result = author._asdict()
            new_authors.append(AuthorSearchResult.parse_obj(dict_result))
    return new_authors

async def get_author_query_no_requests(
    query: ScopusAuthorSearchQuery,
    client: ClientSession,
) -> int:
    term = query_to_term(query.dict()['__root__'])
    request_search = AuthorSearch(term, download = False)
    store_quota_in_cache(request_search)
    return request_search.get_results_size()//Length.AUTHOR_LENGTH +2

async def get_author_query_remaining_in_cache() -> int:
    try:
        return get_remaining_in_cache('AuthorSearch')
    except TypeError:
        return Allowance.AUTH_START_ALLOWANCE

async def affiliation_search_on_query(
    query: AffiliationSearchQuery,
    client: ClientSession,
) -> List[AffiliationSearchResult]:
    term = query_to_term(query.dict()['__root__'])
    affil_results = AffiliationSearch(term, verbose = True)
    store_quota_in_cache(affil_results)
    affiliations = affil_results.affiliations
    new_affiliations =[]
    if affiliations is not None:
        for affiliation in affiliations:
            dict_result = affiliation._asdict()
            new_affiliations.append(AffiliationSearchResult.parse_obj(dict_result))
    return new_affiliations

async def get_affiliation_query_no_requests(
    query: AffiliationSearchQuery,
    client: ClientSession,
) -> int:
    term = query_to_term(query.dict()['__root__'])
    request_search = AffiliationSearch(term, download = False)
    store_quota_in_cache(request_search)
    return request_search.get_results_size()//Length.AFFIL_LENGTH +2

async def get_affiliation_query_remaining_in_cache() -> int:
    try:
        return get_remaining_in_cache('AffiliationSearch')
    except TypeError:
        return Allowance.AFFIL_START_ALLOWANCE

