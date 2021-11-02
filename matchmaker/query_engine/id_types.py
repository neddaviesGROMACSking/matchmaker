#from examples.selector_trial import Selector
from matchmaker.query_engine.abstract_selector_types import BaseSelector
from pydantic import BaseModel, root_validator
from typing import Optional, Literal, List, Tuple, TypeVar, Union
from matchmaker.query_engine.abstract_data_types import BaseData
from enum import Enum

# Datatype invarient: Every field of this model uniquely identifies a paper
class PaperIDSelector(BaseSelector['PaperIDSelector']):
    doi: bool = False
    pubmed_id: bool = False
    scopus_id: bool = False

class PaperIDDef(BaseModel):
    doi: Optional[str] = None
    pubmed_id: Optional[str] = None
    scopus_id: Optional[str] = None

class BasePaperID(BaseData[PaperIDSelector]):
    """
    @root_validator(allow_reuse=True)
    def one_or_more_selected(cls, values):
        selected_ids = []
        for id_name, id_value in values.items():
            if id_value is not None:
                selected_ids.append(id_value)
        if len(selected_ids)==0:
            raise ValueError('No ids selected')
        return values
    """
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

PaperID = BasePaperID.generate_model_from_selector()

class PubmedId(BaseModel):
    author_name: str
    proc_institution: List[Tuple[str, str]]

class AuthorId(BaseModel):
    scopus_id: Optional[str] = None
    pubmed_id: Optional[PubmedId] = None
    @root_validator(allow_reuse=True)
    def one_or_more_selected(cls, values):
        selected_ids = []
        for id_name, id_value in values.items():
            if id_value is not None:
                selected_ids.append(id_value)
        if len(selected_ids)==0:
            raise ValueError('No ids selected')
        return values
