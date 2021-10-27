from matchmaker.query_engine.backends.pubmed import PaperSearchQueryEngine
from matchmaker.query_engine.query_types import PaperSearchQuery
from matchmaker.query_engine.backends.pubmed_api import PubmedESearchQuery
from matchmaker.query_engine.backends import NewAsyncClient, RateLimiter
import asyncio

import time
from secret import pubmed_api_key
import aiohttp
d = {
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'author',
                'operator': {
                    'tag': 'equal',
                    'value': 'Jeremy Green'
                }
            },
            {
                'tag': 'year',
                'operator': {
                    'tag': 'range',
                    'lower_bound': '2001',
                    'upper_bound': '2012'
                }
            }
        ]
    }
}

rate_limiter = RateLimiter()

pub_searcher = PaperSearchQueryEngine(pubmed_api_key, rate_limiter)

start = time.time()
async def main():
    query = PaperSearchQuery.parse_obj(d)
    proc_result = await pub_searcher(query)
    return proc_result
results = asyncio.run(main())
#print(results[0])
print(len(str(results)))
#print(results[-1])
end = time.time()
print(end-start)