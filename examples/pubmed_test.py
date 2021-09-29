from matchmaker.query_engine.backends.pubmed import PaperSearchQueryEngine
from matchmaker.query_engine.query_types import PaperSearchQuery
from matchmaker.query_engine.backends.pubmed_api import PubmedESearchQuery
from matchmaker.query_engine.backends import NewAsyncClient
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


pub_searcher = PaperSearchQueryEngine(api_key=pubmed_api_key)


start = time.time()
async def main():
    query = PaperSearchQuery.parse_obj(d)
    #test = await pub_searcher._query_to_native(query)
    #awaitable = test.coroutine_function
    #metadata = test.metadata
    #unproc_result = await pub_searcher._run_native_query(test)
    #proc_result = await pub_searcher._post_process(query, unproc_result)
    proc_result = await pub_searcher(query)
    return proc_result
results = asyncio.run(main())
print(len(str(results)))
print(results[-1])
end = time.time()
print(end-start)