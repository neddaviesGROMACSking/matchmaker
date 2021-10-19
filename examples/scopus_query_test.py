from matchmaker.query_engine.backends.scopus_api_new import ScopusSearchQuery, get_scopus_query_remaining_in_cache, scopus_search_on_query, get_scopus_query_no_requests

d = {
    'tag': 'and',
    'fields_': [
        {
            'tag': 'year',
            'operator': {
                'tag': 'equal',
                'value': 1996
            }
        }
    ]
}

d = {
    'tag': 'auth',
    'operator': {
        'tag': 'equal',
        'value': 'Pink'
    }
}

pq = ScopusSearchQuery.parse_obj(d)
cache_rem = get_scopus_query_remaining_in_cache()
print(cache_rem)
results_length = get_scopus_query_no_requests(pq)
cache_rem = get_scopus_query_remaining_in_cache()
print(cache_rem)
results = scopus_search_on_query(pq)
#print(len(results))
print(results[0])
print(results_length)
cache_rem = get_scopus_query_remaining_in_cache()
print(cache_rem)
