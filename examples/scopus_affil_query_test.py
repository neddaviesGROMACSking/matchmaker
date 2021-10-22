from matchmaker.query_engine.backends.scopus_api_new import (
    AffiliationSearchQuery,
    affiliation_search_on_query,
    get_affiliation_query_no_requests,
    get_affiliation_query_remaining_in_cache,
)
import asyncio
from secret import scopus_api_key, scopus_inst_token
d = {
    'tag': 'affiliation',
    'operator': {
        'tag': 'equal',
        'value': "Scotland"
    }
}


pq = AffiliationSearchQuery.parse_obj(d)
async def main():
    cache_rem = await get_affiliation_query_remaining_in_cache()
    print(cache_rem)
    results_length = await get_affiliation_query_no_requests(pq, None, scopus_api_key, scopus_inst_token)
    cache_rem = await get_affiliation_query_remaining_in_cache()
    print(cache_rem)
    results = await affiliation_search_on_query(pq, None, scopus_api_key, scopus_inst_token)
    #print(len(results))
    print(results[2])
    print(results_length)
    cache_rem = await get_affiliation_query_remaining_in_cache()
    print(cache_rem)
asyncio.run(main())