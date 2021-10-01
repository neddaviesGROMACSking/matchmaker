from matchmaker.query_engine.backends.pubmed import AuthorSearchQueryEngine
from matchmaker.query_engine.query_types import AuthorSearchQuery
from matchmaker.query_engine.backends.pubmed_api import PubmedESearchQuery
from matchmaker.query_engine.backends import NewAsyncClient, RateLimiter
import asyncio

import time
from secret import pubmed_api_key
import aiohttp
d = {
    'tag': 'and',
    'fields_': [
        {
            'tag': 'author',
            'operator': {
                'tag': 'equal',
                'value': 'Jeremy Green'
            }
        }
    ]
}

rate_limiter = RateLimiter()

pub_searcher = AuthorSearchQueryEngine(pubmed_api_key, rate_limiter)

start = time.time()
async def main():
    query = AuthorSearchQuery.parse_obj(d)
    proc_result = await pub_searcher(query)
    return proc_result
results = asyncio.run(main())
print(len(str(results)))

print(results[0])
end = time.time()
print(end-start)