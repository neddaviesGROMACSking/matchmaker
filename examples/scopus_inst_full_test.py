from matchmaker.query_engine.backends.scopus import InstitutionSearchQueryEngine
from matchmaker.query_engine.types.query import InstitutionSearchQuery
from matchmaker.query_engine.backends.web import RateLimiter
import asyncio

import time
from secret import scopus_api_key, scopus_inst_token
d = {
    'query':{
        'tag': 'institution',
        'operator': {
            'tag': 'equal',
            'value': 'Queen Marys College'
        }
    }
}

rate_limiter = RateLimiter()

pub_searcher = InstitutionSearchQueryEngine(scopus_api_key,scopus_inst_token, rate_limiter)

start = time.time()
async def main():
    query = InstitutionSearchQuery.parse_obj(d)
    proc_result = await pub_searcher(query)
    return proc_result
results = asyncio.run(main())
print(results)
print(len(str(results)))
#print(results[-1])
end = time.time()
print(end-start)
