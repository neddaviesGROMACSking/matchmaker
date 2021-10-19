from matchmaker.query_engine.backends.scopus_api_new import (
    AffiliationSearchQuery,
    affiliation_search_on_query,
    get_affiliation_query_no_requests,
    get_affiliation_query_remaining_in_cache,
)

d = {
    'tag': 'affiliation',
    'operator': {
        'tag': 'equal',
        'value': "Scotland"
    }
}


pq = AffiliationSearchQuery.parse_obj(d)
cache_rem = get_affiliation_query_remaining_in_cache()
print(cache_rem)
results_length = get_affiliation_query_no_requests(pq)
cache_rem = get_affiliation_query_remaining_in_cache()
print(cache_rem)
results = affiliation_search_on_query(pq)
#print(len(results))
print(results[2])
print(results_length)
cache_rem = get_affiliation_query_remaining_in_cache()
print(cache_rem)
