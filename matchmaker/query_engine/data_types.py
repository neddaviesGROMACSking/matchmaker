from pydantic import BaseModel
from typing import Generic, Union, List, Optional, Tuple, Dict, TypeVar
from matchmaker.query_engine.id_types import PaperIDDef, PaperID
from matchmaker.query_engine.selector_types import InstitutionDataSelector, AuthorDataSelector, PaperDataSelector
from matchmaker.query_engine.abstract_selector_types import BaseSelector
from matchmaker.query_engine.abstract_data_types import BaseData

SelectorType = TypeVar('SelectorType', bound = BaseSelector)

class InstitutionDataDef(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    processed: Optional[List[Tuple[str, str]]] = None
    paper_count: Optional[int] = None
    name_variants: Optional[List[str]] = None

InstitutionDataDef.__name__ = 'InstitutionData'

class InstitutionData(BaseData[InstitutionDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, InstitutionDataSelector] = True):
        return super().generate_model_from_selector(InstitutionDataDef, selector)

class AuthorDataDef(BaseModel):
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
    institution_current: Optional[InstitutionDataDef] = None
    other_institutions: List[InstitutionDataDef] = []
    paper_count: Optional[int] = None
    paper_ids: Optional[List[PaperIDDef]] = []

AuthorDataDef.__name__ = 'AuthorData'

class AuthorData(BaseData[AuthorDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, SelectorType] = True):
        return super().generate_model_from_selector(
            AuthorDataDef, 
            selector,
            {
                'institution_current': InstitutionData,
                'other_institutions': InstitutionData,
                'paper_ids': PaperID
            }
        )

class Topic(BaseModel):
    descriptor: Optional[str]
    qualifier: Optional[str]

class SubPaperData(BaseModel):
    paper_id: PaperIDDef
    title: str
    authors: List[AuthorDataDef]
    year: Optional[int]
    source_title: str
    source_title_id: Optional[str] = None
    source_title_abr: Optional[str] = None
    abstract: Optional[Union[str, List[Tuple[Optional[str], Optional[str]]]]] = None
    institutions: Optional[List[InstitutionDataDef]] = None
    keywords: Optional[List[str]] = None
    topics: Optional[List[Topic]] = None

class PaperDataDef(SubPaperData):
    references: Optional[Union[int, List[SubPaperData]]] = None
    cited_by: Optional[Union[int, List[SubPaperData]]] = None

PaperDataDef.__name__ = 'PaperData'

class PaperData(BaseData[PaperDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, SelectorType] = True):
        return super().generate_model_from_selector(
            PaperDataDef, 
            selector,
            {
                'institutions': InstitutionData,
                'authors': AuthorData,
                'institution_current': InstitutionData,
                'other_institutions': InstitutionData,
                'paper_id': PaperID
            }
        )
