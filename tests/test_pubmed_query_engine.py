import pytest
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.types.query import And, AuthorName, PaperSearchQuery, PaperIDHigh, EqualPredicate, Title
from tests.conftest import pubmed_author_engine

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
    
    async def test_pubmed_paper_engine_one_title(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = Title(
                    operator = EqualPredicate(
                        value = 'Fluorescently Labelled ATP Analogues for Direct Monitoring of Ubiquitin Activation.'
                    )
                ),
                selector = {'title': True, 'source_title': True}
            )
        )
        results = [i async for i in results]
        assert len(results) == 1
        result = results[0]
        assert result == 1
        assert result.title == 'Fluorescently Labelled ATP Analogues for Direct Monitoring of Ubiquitin Activation.'

    async def test_pubmed_paper_engine_one_author_name(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        Title(
                            operator = EqualPredicate(
                                value = 'Fluorescently Labelled ATP Analogues for Direct Monitoring of Ubiquitin Activation'
                            )
                        ),
                        AuthorName(
                            operator = EqualPredicate(
                                value = 'Stuber'
                            )
                        )
                    ]
                ),
                selector = {
                    'authors': {'preferred_name': {'surname': True}}
                }
            )
        )
        results = [i async for i in results]
        assert len(results) == 1
        result = results[0]
        authors = result.authors
        relevant_author_names = [author.preferred_name.surname for author in authors if author.preferred_name.surname == 'Stuber']
        assert len(relevant_author_names) >= 1
