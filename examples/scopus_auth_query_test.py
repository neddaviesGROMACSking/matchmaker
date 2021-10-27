from matchmaker.query_engine.backends.scopus.api import (
    ScopusAuthorSearchQuery,
    author_search_on_query,
    get_author_query_no_requests,
    get_author_query_remaining_in_cache,
)
import asyncio
from secret import scopus_api_key, scopus_inst_token
d = {
    'query':{
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
}

pq = ScopusAuthorSearchQuery.parse_obj(d)
async def main():
    cache_rem = await get_author_query_remaining_in_cache()
    print(cache_rem)
    results_length = await get_author_query_no_requests(pq, None, scopus_api_key, scopus_inst_token)
    cache_rem = await get_author_query_remaining_in_cache()
    print(cache_rem)
    results = await author_search_on_query(pq, None, scopus_api_key, scopus_inst_token)
    #print(len(results))
    print(results[0])
    print(results_length)
    cache_rem = await get_author_query_remaining_in_cache()
    print(cache_rem)
asyncio.run(main())