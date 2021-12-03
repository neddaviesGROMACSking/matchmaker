from matchmaker.query_engine.backends.scopus import AuthorSearchQueryEngine
from matchmaker.query_engine.types.query import AuthorSearchQuery
from matchmaker.query_engine.backends.web import RateLimiter
import asyncio

import time
from secret import scopus_api_key, scopus_inst_token

d = {
    'query':{
        'tag': 'or',
        'fields_': [
            {
                'tag': 'author',
                'operator': {
                    'tag': 'equal',
                    'value': 'Jeremy Green'
                }
            },
            {
                'tag': 'author',
                'operator': {
                    'tag': 'equal',
                    'value': 'Ian Rowlands'
                }
            }
        ]
    }
}
rate_limiter = RateLimiter()

pub_searcher = AuthorSearchQueryEngine(scopus_api_key,scopus_inst_token, rate_limiter)

start = time.time()
async def main():
    query = AuthorSearchQuery.parse_obj(d)
    proc_result_iter = await pub_searcher(query)
    proc_result = [i async for i in proc_result_iter]
    return proc_result
results = asyncio.run(main())
print(results[0])
print(len(results))
#print(results[-1])
end = time.time()
print(end-start)
