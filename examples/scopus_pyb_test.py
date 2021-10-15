from matchmaker.query_engine.backends.scopus_utils import create_config
from secret import scopus_inst_token, scopus_api_key
#from matchmaker.query_engine.backends.scopus import ScopusSearch
from pybliometrics.scopus import ScopusSearch, AffiliationSearch, AuthorSearch
from typing import Optional
import requests
from matchmaker.query_engine.backends.scopus_quota_cache import get_remaining_in_cache, get_reset_in_cache, store_quota_in_cache

from pprint import pprint

#get_remaining_in_cache('AuthorSearch', 3434)
create_config(scopus_api_key, scopus_inst_token)

scopus_results = ScopusSearch("AUTH(Jeremy Green)")

from pydantic import BaseModel

class ScopusSearchResult(BaseModel):
    eid:Optional[str]
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

class AffiliationSearchResult(BaseModel):
    eid: str
    name: str
    variant: Optional[str]
    documents: int
    city: str
    country: str
    parent: str

#new_results = []
paper_results = scopus_results.results
#for result in scopus_results.results:
#    dict_result = result._asdict()
#    new_results.append(ScopusSearchResult.parse_obj(dict_result))

#
#affil_results = AffiliationSearch("AFFIL(Max Planck Institute for Innovation and Competition Munich)")
#affil_results = AffiliationSearch("AFFIL(Max Planck Institute)")
affil_out = AffiliationSearch("AFFIL(Kings College London)")
#print(affil_out)
affil_results = affil_out.affiliations
new_results = []
new_afids = []
for affiliation in affil_results:
    dict_result = affiliation._asdict()
    proc_result = AffiliationSearchResult.parse_obj(dict_result)
    new_results.append(proc_result)
    new_afids.append(proc_result.eid.split('-')[-1])
#print(new_results[0])
#print(new_afids)
query = f"AF-ID({new_afids[0]}) AND ((AUTHLASTNAME(GREENNN) AND AUTHFIRST(JEREMY)) OR (AUTHLASTNAME(ROWLANDS) AND AUTHFIRST(IAN)))"
#print(query)
author_results = AuthorSearch(query, verbose = True)


store_quota_in_cache(author_results)

print(get_remaining_in_cache(author_results))
print(get_reset_in_cache(author_results))
