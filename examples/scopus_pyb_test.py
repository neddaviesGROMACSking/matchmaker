from matchmaker.query_engine.backends.scopus_utils import create_config
from secret import scopus_inst_token, scopus_api_key
#from matchmaker.query_engine.backends.scopus import ScopusSearch
from pybliometrics.scopus import ScopusSearch, AffiliationSearch, AuthorSearch
from typing import Optional, List

from matchmaker.query_engine.backends.scopus_quota_cache import get_remaining_in_cache, get_reset_in_cache, store_quota_in_cache
from matchmaker.query_engine.backends.scopus_api_new import AffiliationSearchResult, AuthorSearchResult, ScopusSearchResult
from pprint import pprint

#get_remaining_in_cache('AuthorSearch', 3434)
create_config(scopus_api_key, scopus_inst_token)

scopus_results = ScopusSearch("AUTH(Jeremy Green)")
#scopus_results = ScopusSearch("AUTHOR-NAME(Green, j) AND AFFIL(Kings College London)")
from pydantic import BaseModel
print(scopus_results)

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
query = f"AF-ID({new_afids[0]}) AND ((AUTHLASTNAME(GREEN) AND AUTHFIRST(JEREMY)) OR (AUTHLASTNAME(ROWLANDS) AND AUTHFIRST(IAN)))"
#print(query)
author_results = AuthorSearch(query, verbose = True)
new_author_results = []
for author in author_results.authors:
    """
    # For post process
    subject_list = author.areas.split('; ')
    subject_list_proc = []
    for i in subject_list:
        subject = i[0:4]
        doc_count = i[6:-1]
        subject_list_proc.append({
            'name': subject,
            'doc_count': doc_count
        })
    """
    dict_result = author._asdict()
    new_author = AuthorSearchResult.parse_obj(dict_result)
    new_author_results.append(new_author)

print(new_author_results)
store_quota_in_cache(author_results)

print(get_remaining_in_cache(author_results))
print(get_reset_in_cache(author_results))
