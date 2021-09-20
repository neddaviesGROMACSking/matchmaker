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
    class Name(BaseModel):
        surname: str
        given_names: Optional[str] = None
        initials: Optional[str] = None
    class Subject(BaseModel):
        name: str
        paper_frequency: int
    class Institution(BaseModel):
        name: str
        id: Optional[str] = None
    preferred_name: Name
    name_variants: List[Name]
    subjects: List[Subject]
    institution_current: Institution
    other_institutions: List[Institution] = []
