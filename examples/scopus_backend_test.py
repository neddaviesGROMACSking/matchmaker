from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.backends.scopus import ScopusBackend
from matchmaker.query_engine.selector_types import PaperDataSelector
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

    #'selector': paper_searcher.complete_fields.dict()
    'selector': PaperDataSelector.parse_obj({
        'paper_id':{'doi': True},
        'institutions':{'id': True},
        'authors': {'other_institutions': {'id': True}}
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



async def main():
    paper_results = await paper_searcher(paper_search)
    
    #author_results = await author_searcher(author_search)
   
    #inst_results = await inst_searcher(inst_search)
    return paper_results
paper_results = asyncio.run(main())
print(paper_results[0:4])