from matchmaker.query_engine.types.query import PaperSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from secret import pubmed_api_key
import asyncio
pubmed_backend = PubmedBackend(api_key=pubmed_api_key)
paper_searcher = pubmed_backend.paper_search_engine()
author_search = AuthorSearchQuery.parse_obj({
    'query':{
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
})

paper_search = PaperSearchQuery.parse_obj({
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
    },
    'selector': {
        'authors':{
            'preferred_name': {
                'surname': True,
                'given_names': True}, 
            #'institution_current': {'name': True}
        }
    }
})

async def main():
    data = await paper_searcher(paper_search)
    metadata = await data.metadata()
    results = [i async for i in data]
    #return results, metadata
    print(metadata)
    return results
results = asyncio.run(main())

print(results)
#paper_results, metadata = asyncio.run(main())
#print(metadata)