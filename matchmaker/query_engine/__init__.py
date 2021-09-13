from enum import Enum

from .backends.pubmed import PubMedBackend


class Backends(Enum):
    pubmed = PubMedBackend
