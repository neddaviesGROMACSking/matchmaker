from matchmaker.query_engine.backends.scopus_api_new import ScopusSearchQuery, get_scopus_query_remaining_in_cache, scopus_search_on_query, get_scopus_query_no_requests
import asyncio
from secret import scopus_api_key, scopus_inst_token
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
async def main():
    cache_rem = await get_scopus_query_remaining_in_cache()
    print(cache_rem)
    results_length = await get_scopus_query_no_requests(pq, None, 'COMPLETE', scopus_api_key, scopus_inst_token)
    cache_rem = await get_scopus_query_remaining_in_cache()
    print(cache_rem)
    results = await scopus_search_on_query(pq, None, 'COMPLETE', scopus_api_key, scopus_inst_token)
    #print(len(results))
    print(results[0])
    print(results_length)
    cache_rem = await get_scopus_query_remaining_in_cache()
    print(cache_rem)
asyncio.run(main())