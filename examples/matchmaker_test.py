from matchmaker.matching_engine.abstract_to_abstract import calculate_set_similarity
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

op_scopus_query_engine = op_scopus_backend.paper_search_engine()

id2 = '7404572266' # Jeremy Green
id1 = '7404572266' # Jeremy Green 89.70
#id1 = '57202528457' # Random author Martin Green 86.37
#id1 = '39560905300' # Random co author of jeremy green 83.33
#id1 = '22988279600' #Albert Einstein 75.76
paper_search1 = PaperSearchQuery.parse_obj({
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'authorid',
                'operator': {
                    'tag': 'equal',
                    'value': id1
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
                    'value': id2
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
    author1_abs = [res.abstract for res in author1_res if res.abstract is not None]
    author2_abs = [res.abstract for res in author2_res if res.abstract is not None]
    sims = calculate_set_similarity(
        author1_abs,
        author2_abs,
    )
    print(sims)
"""
abstracts = [
    "Human machine interface for lab abc computer applications",
    "A survey of user opinion of computer system response time",
    "The EPS user interface management system",
    "System and human system engineering testing of EPS",
    "Relation of user perceived response time to error measurement",
    "The generation of random binary unordered trees",
    "The intersection graph of paths in trees",
    "Graph minors IV Widths of trees and well quasi ordering",
    "Graph minors A survey",
]


doc = [
    "Human computer interaction", 
    "computer science human system"
]

sims = calculate_set_similarity(
    abstracts,
    doc,
)
print(sims)
sims = calculate_set_similarity(
    doc,
    abstracts,
)
print(sims)
"""
res = asyncio.run(main())
