from pydantic import BaseModel
from typing import Generic, Union, List, Optional, Tuple, Dict, TypeVar
from matchmaker.query_engine.id_types import PaperID
from matchmaker.query_engine.selector_types import InstitutionDataSelector, AuthorDataSelector, PaperDataSelector, BaseSelector


SelectorType = TypeVar('SelectorType', bound = BaseSelector)

class BaseData(BaseModel, Generic[SelectorType]):
    @classmethod
    def generate_model_from_selector(
        cls, 
        definition: BaseModel, 
        selector: Union[bool, SelectorType], 
        model_mapper: Dict[str, BaseModel] = {}):
        if isinstance(selector, bool):
            if selector:
                return type(cls.__name__, (definition, cls), {}) 
            else:
                return cls
        else:
            return selector.generate_model(cls, definition, model_mapper)

class InstitutionDataDef(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    processed: Optional[List[Tuple[str, str]]] = None
    paper_count: Optional[int] = None
    name_variants: Optional[List[str]] = None

class BaseInstitutionData(BaseData[InstitutionDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, InstitutionDataSelector] = True):
        return super().generate_model_from_selector(InstitutionDataDef, selector)
                
InstitutionData = BaseInstitutionData.generate_model_from_selector()

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
    paper_ids: Optional[List[PaperID]] = []

class BaseAuthorData(BaseData[AuthorDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, SelectorType] = True):
        return super().generate_model_from_selector(
            AuthorDataDef, 
            selector,
            {
                'institution_current': BaseInstitutionData,
                'other_institutions': BaseInstitutionData
            }
        )

AuthorData = BaseAuthorData.generate_model_from_selector()

class Topic(BaseModel):
    descriptor: Optional[str]
    qualifier: Optional[str]

class SubPaperData(BaseModel):
    paper_id: PaperID
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

class BasePaperData(BaseData[PaperDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, SelectorType] = True):
        return super().generate_model_from_selector(
            PaperDataDef, 
            selector,
            {
                'institutions': BaseInstitutionData,
                'authors': BaseAuthorData,
                'institution_current': BaseInstitutionData,
                'other_institutions': BaseInstitutionData
            }
        )

PaperData = BasePaperData.generate_model_from_selector()
