from pydantic import BaseModel
from typing import Union, List, Optional


class PaperData(BaseModel):
    title: str
    authors: List[str]
    year: int
    source_title: str
    abstract: str
    references: List[str]
    institutions: List[str]
    keywords: List[str]
    cited_by: Optional[List[str]] = None


class AuthorData(BaseModel):
    name: str
    affiliation_current: str
    affiliations: List[str]
