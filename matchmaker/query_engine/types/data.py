from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union
from typing import Dict, Generic, TypeVar, Union

from matchmaker.query_engine.types.selector import (
    AuthorDataSelector,
    BaseSelector,
    InstitutionDataSelector,
    PaperDataSelector,
    PaperIDSelector,
    AuthorIDSelector,
    InstitutionIDSelector
)
from pydantic import BaseModel
from pydantic import BaseModel



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



SelectorType = TypeVar('SelectorType', bound = BaseSelector)

class PubmedInstitutionID(BaseModel):
    proc_institution: List[Tuple[str, str]]

class InstitutionIDDef(BaseModel):
    pubmed_id: Optional[PubmedInstitutionID] = None
    scopus_id: Optional[str] = None

InstitutionIDDef.__name__ = 'InstitutionID'

class InstitutionID(BaseData[InstitutionIDSelector]):
    def __eq__(self, other) -> bool:
        raise NotImplementedError
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, InstitutionIDSelector] = True):
        return super().generate_model_from_selector(
            InstitutionIDDef, 
            selector
        )


class PubmedAuthorID(BaseModel):
    author_name: str
    proc_institution: List[Tuple[str, str]]

class AuthorIDDef(BaseModel):
    pubmed_id: Optional[PubmedAuthorID] = None
    scopus_id: Optional[str] = None

AuthorIDDef.__name__ = 'AuthorID'

class AuthorID(BaseData[AuthorIDSelector]):
    def __eq__(self, other) -> bool:
        if hasattr(self, 'scopus_id') and hasattr(other, 'scopus_id'):
            return self.scopus_id == other.scopus_id
        #elif hasattr(self, 'pubmed_id') and hasattr(other, 'pubmed_id'):
        #    raise NotImplementedError
        else:
            return False
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, AuthorIDSelector] = True):
        return super().generate_model_from_selector(
            AuthorIDDef, 
            selector
        )


class PaperIDDef(BaseModel):
    doi: Optional[str] = None
    pubmed_id: Optional[str] = None
    scopus_id: Optional[str] = None

PaperIDDef.__name__ = 'PaperID'

class PaperID(BaseData[PaperIDSelector]):
    def __eq__(self, other) -> bool:
        common_fields = [i for i in self.__fields__.keys() if i in other.__fields__]
        for id_type in common_fields:
            self_id = getattr(self, id_type)
            other_id = getattr(other, id_type)
            if other_id is not None and self_id is not None:
                if self_id == other_id:
                    return True
        return False
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, PaperIDSelector] = True):
        return super().generate_model_from_selector(
            PaperIDDef, 
            selector
        )



class InstitutionDataDef(BaseModel):
    name: Optional[str] = None
    id: Optional[InstitutionIDDef] = None
    processed: Optional[List[Tuple[str, str]]] = None
    paper_count: Optional[int] = None
    name_variants: Optional[List[str]] = None

InstitutionDataDef.__name__ = 'InstitutionData'

class InstitutionData(BaseData[InstitutionDataSelector]):
    @classmethod
    def generate_model_from_selector(cls, selector: Union[bool, InstitutionDataSelector] = True):
        return super().generate_model_from_selector(
            InstitutionDataDef, 
            selector,
            {
                'id': InstitutionID
            })

class AuthorDataDef(BaseModel):
    class Name(BaseModel):
        surname: str
        given_names: Optional[str] = None
        initials: Optional[str] = None
    class Subject(BaseModel):
        name: str
        paper_count: int
    preferred_name: Name
    id: Optional[AuthorIDDef] = None
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
                'paper_ids': PaperID,
                'id': AuthorID
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
