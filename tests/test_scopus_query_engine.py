import pytest
from matchmaker.query_engine.backends.scopus import ScopusBackend
from matchmaker.query_engine.types.query import PaperSearchQuery

@pytest.mark.asyncio
class TestScopusBackend:
    async def test_backend_generation(self, scopus_api_key, scopus_inst_token):
        scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)

    async def test_paper_engine_generation(self, scopus_api_key, scopus_inst_token):
        scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)
        paper_engine = scopus_backend.paper_search_engine()

    async def test_author_engine_generation(self, scopus_api_key, scopus_inst_token):
        scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)
        author_engine = scopus_backend.author_search_engine()

    async def test_institution_engine_generation(self, scopus_api_key, scopus_inst_token):
        scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)
        institution_engine = scopus_backend.institution_search_engine()

@pytest.mark.asyncio
class TestPaperEngine:
    async def test_scopus_paper_engine_one_id(self, scopus_paper_engine):
        results = await scopus_paper_engine(
            PaperSearchQuery.parse_obj(
                {
                    'query': {
                        'tag': 'id',
                        'operator': {
                            'tag': 'equal',
                            'value': {
                                'doi': '10.1242/dev.197293'
                            }
                        }
                    }, 
                    'selector': {'paper_id':{'doi': True}}}
            )
        )
        assert len(results) ==1
        result = results[0]
        assert result.paper_id.doi == '10.1242/dev.197293'
       
