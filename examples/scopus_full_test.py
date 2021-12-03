from matchmaker.query_engine.backends.scopus import PaperSearchQueryEngine
from matchmaker.query_engine.types.query import PaperSearchQuery
from matchmaker.query_engine.backends.web import RateLimiter
import asyncio

import time
from secret import scopus_api_key, scopus_inst_token
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

pub_searcher = PaperSearchQueryEngine(scopus_api_key,scopus_inst_token, rate_limiter)

start = time.time()
async def main():
    query = PaperSearchQuery.parse_obj(d)
    proc_result_iter = await pub_searcher(query)
    proc_result = [i async for i in proc_result_iter]
    return proc_result
results = asyncio.run(main())
#print(results[0])
print(len(str(results)))
#print(results[-1])
end = time.time()
print(end-start)