from matchmaker.matching_engine.abstract_to_abstract import calculate_set_similarity
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

op_scopus_query_engine = op_scopus_backend.paper_search_engine()

op_scopus_query_engine = op_scopus_backend.paper_search_engine()

id2 = '7404572266' # Jeremy Green
id1 = '7404572266' # Jeremy Green med: 90.6 av: 80.9 av2: 71.7 # av_sing: 79.8
id1 = '57202528457' # Martin Green makes solar cells med: 92.5 av: 84.7 av2: 75.7 # av_sing: 84.8
#id1 = '39560905300' # Random co author of jeremy green med: 90.2 av: 80.9 av2: 70.8 (small doc count) # av_sing: 81.4
id1 = '22988279600' #Albert Einstein med: 82.2 av: 72.1 av2: 62.0 # av_sing: 75.1
#id1 = '7402259702' # William Green laser physicist med: 90.8 av: 80.6 av2: 71.5  # av_sing: 82.6
#id1 = '24605680400' # James Smith colleague of Jeremy Green med: 90.7 av: 82.6 av2: 72.6  # av_sing: 82.4
#id1 = '16445638600' # Babette Babich Philosopher med: 82.5 av: 67.8 av2: 58.5  # av_sing: 80.4
paper_search1 = PaperSearchQuery.parse_obj({
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'authorid',
                'operator': {
                    'tag': 'equal',
                    'value': {'scopus_id': id1}
                }
            }
            #{
            #    'tag': 'year',
            #    'operator': {
            #        'tag': 'range',
            #        'lower_bound': '2001',
            #        'upper_bound': '2012'
            #    }
            #}
            
        ]
    },
    'selector': {
        'paper_id': True,
        'abstract': True
    }
})
paper_search2 = PaperSearchQuery.parse_obj({
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'authorid',
                'operator': {
                    'tag': 'equal',
                    'value': {'scopus_id': id2}
                }
            }
            
            #{
            #    'tag': 'year',
            #    'operator': {
            #        'tag': 'range',
            #        'lower_bound': '2001',
            #        'upper_bound': '2012'
            #    }
            #}
            
        ]
    },
    'selector': {
        'paper_id': True,
        'abstract': True
    }
})


async def main():
    author1_res = await op_scopus_query_engine(paper_search1)
    author2_res = await op_scopus_query_engine(paper_search2)
    author1_abs = [res.abstract async for res in author1_res if res.abstract is not None]
    author2_abs = [res.abstract async for res in author2_res if res.abstract is not None]
    sims = calculate_set_similarity(
        author1_abs,
        author2_abs,
    )
    print(sims)

res = asyncio.run(main())
