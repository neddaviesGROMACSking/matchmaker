from matchmaker.query_engine.backends.pubmed import PaperSearchQueryEngine
from matchmaker.query_engine.query_types import PaperSearchQuery
from matchmaker.query_engine.backends.pubmed_api import PubmedESearchQuery
from matchmaker.query_engine.backends import NewAsyncClient
import asyncio
from httpx import AsyncClient
import time
from secret import pubmed_api_key
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
    test = pub_searcher._query_to_native(PaperSearchQuery.parse_obj(d))
    #test = PubmedESearchQuery.parse_obj(d)
    awaitable, metadata = pub_searcher._query_to_awaitable(test)
    # Run native query
    print(awaitable)
    async with NewAsyncClient() as client:
        test = await awaitable(client)
    return test
results = asyncio.run(main())
print(len(str(results)))
end = time.time()
print(end-start)