from matchmaker.query_engine.backends import exceptions
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend
import pytest

try:
    from secret import scopus_api_key as scopus_api_key_original
except ImportError:
    raise ValueError('Scopus api key required for tests')
try:
    from secret import scopus_inst_token as scopus_inst_token_original
except ImportError:
    raise ValueError('Scopus institution token required for tests')

try:
    from secret import pubmed_api_key as pubmed_api_key_original
except ImportError:
    raise ValueError('Pubmed api key required for tests')

@pytest.fixture
async def scopus_api_key():
    return scopus_api_key_original

@pytest.fixture
async def scopus_inst_token():
    return scopus_inst_token_original


@pytest.fixture
async def scopus_paper_engine(scopus_api_key, scopus_inst_token):
    backend = ScopusBackend(scopus_api_key, scopus_inst_token)
    return backend.paper_search_engine()

@pytest.fixture
async def scopus_author_engine(scopus_api_key, scopus_inst_token):
    backend = ScopusBackend(scopus_api_key, scopus_inst_token)
    return backend.author_search_engine()

@pytest.fixture
async def scopus_institution_engine(scopus_api_key, scopus_inst_token):
    backend = ScopusBackend(scopus_api_key, scopus_inst_token)
    return backend.institution_search_engine()

@pytest.fixture
async def pubmed_api_key():
    return pubmed_api_key_original

@pytest.fixture
async def pubmed_paper_engine(pubmed_api_key):
    backend = PubmedBackend(pubmed_api_key)
    return backend.paper_search_engine()

@pytest.fixture
async def pubmed_author_engine(pubmed_api_key):
    backend = PubmedBackend(pubmed_api_key)
    return backend.author_search_engine()

@pytest.fixture
async def pubmed_institution_engine(pubmed_api_key):
    backend = PubmedBackend(pubmed_api_key)
    return backend.institution_search_engine()
