from matchmaker.query_engine.backends.scopus_api_new import (
    ScopusAuthorSearchQuery,
    author_search_on_query,
    get_author_query_no_requests,
    get_author_query_remaining_in_cache,
)
import asyncio
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

pq = ScopusAuthorSearchQuery.parse_obj(d)
async def main():
    cache_rem = get_author_query_remaining_in_cache()
    print(cache_rem)
    results_length = await get_author_query_no_requests(pq, None)
    cache_rem = await get_author_query_remaining_in_cache()
    print(cache_rem)
    results = await author_search_on_query(pq, None)
    #print(len(results))
    print(results[0])
    print(results_length)
    cache_rem = await get_author_query_remaining_in_cache()
    print(cache_rem)
asyncio.run(main())