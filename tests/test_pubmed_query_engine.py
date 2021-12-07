import pytest
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.types.query import Abstract, And, AuthorName, Keyword, PaperSearchQuery, PaperIDHigh, EqualPredicate, Title, Journal, Institution, Year, Topic
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
                selector = {'title': True}
            )
        )
        results = [i async for i in results]
        assert len(results) == 1
        result = results[0]
        assert result.title == 'Fluorescently Labelled ATP Analogues for Direct Monitoring of Ubiquitin Activation.'

    async def test_pubmed_paper_engine_one_author_name(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
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

    async def test_pubmed_paper_engine_one_journal(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
                            )
                        ),
                        Journal(
                            operator = EqualPredicate(
                                value = 'Chemistry (Weinheim an der Bergstrasse, Germany)'
                            )
                        )
                    ]
                ),
                selector = {
                    'source_title': True
                }
            )
        )
        
        results_list = [i async for i in results]
        assert results_list == 1
        result = results_list[0]
        assert result.source_title == 'Chemistry (Weinheim an der Bergstrasse, Germany)'

    async def test_pubmed_paper_engine_one_abstract(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
                            )
                        ),
                        Abstract(
                            operator = EqualPredicate(
                                value = 'Simple and robust assays to monitor enzymatic ATP cleavage with high efficiency'
                            )
                        )
                    ]
                ),
                selector = {
                    'abstract': True
                }
            )
        )
        
        results_list = [i async for i in results]
        assert len(results_list) ==1 
        result = results_list[0]

        assert 'Simple and robust assays to monitor enzymatic ATP cleavage with high efficiency' == result.abstract[0][1][0:79]

    async def test_pubmed_paper_engine_one_institution(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
                            )
                        ),
                        Institution(
                            operator = EqualPredicate(
                                value = 'Department of Chemistry, University of Konstanz'
                            )
                        )
                    ]
                ),
                selector = {
                    'institutions': True
                }
            )
        )
        
        # assert 'Department of Chemistry, University of Konstanz' in results
        # results_list = [i async for i in results]
        # assert len(results_list) == 1 
        # result = results_list[0]
        # assert 'Department of Chemistry, University of Konstanz' in result.institutions

    async def test_pubmed_paper_engine_one_keyword(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
                            )
                        ),
                        Keyword(
                            operator = EqualPredicate(
                                value = 'ATP'
                            )
                        ), 
                        Keyword(
                            operator = EqualPredicate(
                                value = 'PET'
                            )
                        ),
                        Keyword(
                            operator = EqualPredicate(
                                value = 'UBA1'
                            )
                        )                        
                    ]
                ),
                selector = {
                    'keywords': True
                }
            )
        )
        
        results_list = [i async for i in results]
        assert len(results_list) == 1 
        result = results_list[0]
        assert all(x in result.keywords for x in ['ATP', 'PET', 'UBA1'])

    async def test_pubmed_paper_engine_one_year(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
                            )
                        ),
                        Year(
                            operator = EqualPredicate(
                                value = 2020
                            )
                        )
                    ]
                ),
                selector = {
                    'year': True
                }
            )
        )
        
        results_list = [i async for i in results]
        assert len(results_list) == 1 
        result = results_list[0]
        assert 2020 == result.year

    async def test_pubmed_paper_engine_one_topic(self, pubmed_paper_engine):
        results = await pubmed_paper_engine(
            PaperSearchQuery(
                query = And(
                    fields_ = [
                        PaperIDHigh(
                            operator = EqualPredicate(
                                value = {
                                    'doi':'10.1002/chem.202001091'
                                }
                            )
                        ),
                        Topic(
                            operator = EqualPredicate(
                                value = 'Adenosine Triphosphate'
                            )
                        )
                    ]
                ),
                selector = {
                    'topics': True
                }
            )
        )
        
        results_list = [i async for i in results]
        assert len(results_list) == 1 
        result = results_list[0]
        assert 'Adenosine Triphosphate' in result.topics
        
