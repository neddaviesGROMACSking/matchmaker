from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery, InstitutionSearchQuery
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend
from secret import pubmed_api_key, scopus_api_key, scopus_inst_token
import asyncio
author_search = AuthorSearchQuery.parse_obj({
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
})

paper_search = PaperSearchQuery.parse_obj({
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
})

inst_search = InstitutionSearchQuery.parse_obj({
    'tag': 'institution',
    'operator': {
        'tag': 'equal',
        'value': "Scotland"
    }
})
pubmed_backend = PubmedBackend(api_key=pubmed_api_key)
scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)
async def main():
    pub_paper_searcher = pubmed_backend.paper_search_engine()
    pub_author_searcher = pubmed_backend.author_search_engine()
    sco_paper_searcher = scopus_backend.paper_search_engine()
    sco_author_searcher = scopus_backend.author_search_engine()
    sco_inst_searcher = scopus_backend.institution_search_engine()

    pub_paper_results = await pub_paper_searcher(paper_search)
    pub_author_results = await pub_author_searcher(author_search)
    sco_paper_results = await sco_paper_searcher(paper_search)
    sco_author_results = await sco_paper_searcher(author_search)
    sco_inst_results = await sco_inst_searcher(inst_search)

    return pub_paper_results
pub_paper_results = asyncio.run(main())
