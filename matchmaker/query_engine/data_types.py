from pydantic import BaseModel
from typing import Union, List, Optional, Tuple, Dict
from matchmaker.query_engine.id_types import PaperID

class BaseInstitutionData(BaseModel):
    pass

class InstitutionData(BaseInstitutionData):
    name: Optional[str] = None
    id: Optional[str] = None
    processed: Optional[List[Tuple[str, str]]] = None
    paper_count: Optional[int] = None
    name_variants: Optional[List[str]] = None

class BaseAuthorData(BaseModel):
    pass

class AuthorData(BaseAuthorData):
    class Name(BaseModel):
        surname: str
        given_names: Optional[str] = None
        initials: Optional[str] = None
    class Subject(BaseModel):
        name: str
        paper_count: int
    preferred_name: Name
    id: Optional[str] = None
    name_variants: List[Name] = []
    subjects: List[Subject] = []
    institution_current: Optional[InstitutionData] = None
    other_institutions: List[InstitutionData] = []
    paper_count: Optional[int] = None
    paper_ids: Optional[List[PaperID]] = []

class Topic(BaseModel):
    descriptor: Optional[str]
    qualifier: Optional[str]

class SubPaperData(BaseModel):
    paper_id: PaperID
    title: str
    authors: List[AuthorData]
    year: Optional[int]
    source_title: str
    source_title_id: Optional[str] = None
    source_title_abr: Optional[str] = None
    abstract: Optional[Union[str, List[Tuple[Optional[str], Optional[str]]]]] = None
    institutions: Optional[List[InstitutionData]] = None
    keywords: Optional[List[str]] = None
    topics: Optional[List[Topic]] = None

class BasePaperData(BaseModel):
    pass

class PaperData(SubPaperData, BasePaperData):
    references: Optional[Union[int, List[SubPaperData]]] = None
    cited_by: Optional[Union[int, List[SubPaperData]]] = None


