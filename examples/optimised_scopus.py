from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery
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

op_scopus_query_engine = op_scopus_backend.paper_search_engine()

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
    'selector': op_scopus_query_engine.possible_searches[1]
})

author_search = AuthorSearchQuery.parse_obj({
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'institution',
                'operator': {
                    'tag': 'equal',
                    'value': 'Kings College'
                }
            },
            {
                'tag': 'author',
                'operator': {
                    'tag': 'equal',
                    'value': 'Smith'
                }
            },
            {
                'tag': 'year',
                'operator': {
                    'tag': 'range',
                    'lower_bound': '2018',
                    'upper_bound': '2022'
                }
            }
        ]
    },
    'selector': {
        'id': True,
        'preferred_name': {'given_names': True},
        'subjects': True
    }
})


op_scopus_author_engine = op_scopus_backend.author_search_engine()
async def main():
    await op_scopus_query_engine(paper_search)
    return await op_scopus_author_engine(author_search)

res = asyncio.run(main())
print(res)
print(len(res))
#print([r.topics for r in res])

#print([res.paper_id.doi for res in res])