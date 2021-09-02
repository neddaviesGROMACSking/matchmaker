from enum import Enum

from .backends.pubmed import QueryEngine \
        as PubMedQueryEngine


class Backends(Enum):
    pubmed = PubMedQueryEngine
