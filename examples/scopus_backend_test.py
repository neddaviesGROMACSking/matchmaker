from typing import AsyncIterator
from matchmaker.query_engine.types.query import PaperSearchQuery, AuthorSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.backends.scopus import ScopusBackend
from matchmaker.query_engine.types.selector import PaperDataSelector
from secret import scopus_api_key, scopus_inst_token
import asyncio
scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)
paper_searcher = scopus_backend.paper_search_engine()

author_searcher = scopus_backend.author_search_engine()
inst_searcher = scopus_backend.institution_search_engine()
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
    },
    'selector':{
        'id': {'scopus_id': True}
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
                    'upper_bound': '2004'
                }
            }
        ]
    },

    #'selector': paper_searcher.complete_fields.dict()
    'selector': PaperDataSelector.parse_obj({
        'paper_id':{'doi': True},
        'institutions':{'id': {'scopus_id': True}},
        'authors': {'other_institutions': {'id': {'scopus_id': True}}}
    })
})
inst_search = InstitutionSearchQuery.parse_obj({
    'query':{
        'tag': 'institution',
        'operator': {
            'tag': 'equal',
            'value': "Scotland"
        }
    },
    'selector':{
        'id': {'scopus_id': True}
    }
})



async def main():
    data = await paper_searcher(paper_search)
    metadata = await data.metadata()
    paper_results = [i async for i in data]
    return paper_results, metadata
paper_results, metadata = asyncio.run(main())
print(paper_results[0:4])
print(metadata)