import pytest
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.types.query import PaperSearchQuery, PaperIDHigh, EqualPredicate

@pytest.mark.asyncio
class TestPubmedBackend:
    async def test_backend_generation(self, pubmed_api_key):
        pubmed_backend = PubmedBackend(pubmed_api_key)

    async def test_paper_engine_generation(self, pubmed_api_key):
        pubmed_backend = PubmedBackend(pubmed_api_key)
        paper_engine = pubmed_backend.paper_search_engine()

    async def test_author_engine_generation(self, pubmed_api_key):
        pubmed_backend = PubmedBackend(pubmed_api_key)
        #author_engine = pubmed_backend.author_search_engine()

    async def test_institution_engine_generation(self, pubmed_api_key):
        pubmed_backend = PubmedBackend(pubmed_api_key)
        #institution_engine = pubmed_backend.institution_search_engine()

@pytest.mark.asyncio
class TestPaperEngine:
    async def test_pubmed_paper_engine_one_id(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query= PaperIDHigh(  
                    operator = EqualPredicate(
                        value={
                            'doi': '10.1242/dev.197293'
                        }
                    )
                ), 
                selector= {'paper_id':{'doi': True}}
            )
        )

        results_list = [i async for i in results]
        assert len(results_list) == 1
        result = results_list[0]
        assert result.paper_id.doi == '10.1242/dev.197293'