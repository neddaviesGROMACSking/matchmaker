from matchmaker.query_engine.backends.scopus_api_new import (
    AuthorSearchQuery,
    author_search_on_query,
    get_author_query_no_requests,
    get_author_query_remaining_in_cache,
)

d = {
    'tag': 'and',
    'fields_': [
        {
            'tag': 'authfirst',
            'operator': {
                'tag': 'equal',
                'value': 'Jeremy'
            }
        },
        {
            'tag': 'authlast',
            'operator': {
                'tag': 'equal',
                'value': 'Smith'
            },
        }
    ]
}

pq = AuthorSearchQuery.parse_obj(d)
cache_rem = get_author_query_remaining_in_cache()
print(cache_rem)
results_length = get_author_query_no_requests(pq)
cache_rem = get_author_query_remaining_in_cache()
print(cache_rem)
results = author_search_on_query(pq)
#print(len(results))
print(results[0])
print(results_length)
cache_rem = get_author_query_remaining_in_cache()
print(cache_rem)
