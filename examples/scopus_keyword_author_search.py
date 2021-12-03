from matchmaker.query_engine.types.query import PaperSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.backends.optimised_scopus_meta import OptimisedScopusBackend
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend
from secret import pubmed_api_key, scopus_api_key, scopus_inst_token
import asyncio
op_scopus_backend = OptimisedScopusBackend(
    ScopusBackend(
        scopus_api_key,
        scopus_inst_token
    ),
    PubmedBackend(
        pubmed_api_key
    )
)

author_searcher = op_scopus_backend.author_search_engine()
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
            },
            {
                'tag': 'topic',
                'operator': {
                    'tag': 'equal',
                    'value': 'Craniofacial'
                }
            }
        ]
    },
    'selector': {
        'id': {'scopus_id': True}
    }
})
"""
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
    }
})
"""


async def main():
    #paper_results = await paper_searcher(paper_search)
    
    author_results_iter = await author_searcher(author_search)
    author_results =[i async for i in author_results_iter]
    #inst_results = await inst_searcher(inst_search)
    return author_results
author_results = asyncio.run(main())
print(author_results[0:4])