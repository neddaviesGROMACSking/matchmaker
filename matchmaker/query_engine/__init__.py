from enum import Enum

#from .backends.pubmed import PubmedBackend
from .backends.scopus import ScopusBackend


class Backends(Enum):
    #pubmed = PubmedBackend
    scopus = ScopusBackend
