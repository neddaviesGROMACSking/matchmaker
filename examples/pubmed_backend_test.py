from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from secret import pubmed_api_key
import asyncio
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
    }
})
pubmed_backend = PubmedBackend(api_key=pubmed_api_key)
async def main():
    paper_searcher = pubmed_backend.paper_search_engine()
    author_searcher = pubmed_backend.author_search_engine()

    paper_results = await paper_searcher(paper_search)
    author_results = await author_searcher(author_search)
    return paper_results
paper_results = asyncio.run(main())