from pydantic import BaseModel
from typing import Union, List, Optional, Tuple, Dict
from matchmaker.query_engine.id_types import PaperID

class AuthorPaperData(BaseModel):
    paper_id: PaperID


class AuthorData(BaseModel):
    class Name(BaseModel):
        surname: str
        given_names: Optional[str] = None
        initials: Optional[str] = None
    class Subject(BaseModel):
        name: str
        paper_count: int
    class Institution(BaseModel):
        name: Optional[str]
        id: Optional[str] = None
        processed: Optional[List[Tuple[str, str]]] = None
    preferred_name: Name
    name_variants: List[Name] = []
    subjects: List[Subject] = []
    institution_current: Optional[Institution] = None
    other_institutions: List[Institution] = []
    paper_count: Optional[int] = None
    papers: Optional[List[AuthorPaperData]] = []

class Topic(BaseModel):
    descriptor: Optional[str]
    qualifier: Optional[str]

class SubPaperData(BaseModel):
    paper_id: PaperID
    title: str
    authors: List[AuthorData]
    year: Optional[int]
    source_title: str
    source_title_abr: Optional[str] = None
    abstract: Optional[Union[str, List[Tuple[Optional[str], Optional[str]]]]] = None
    institutions: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    topics: Optional[List[Topic]] = None

class PaperData(SubPaperData):
    references: Optional[List[SubPaperData]] = None
    cited_by: Optional[List[SubPaperData]] = None

