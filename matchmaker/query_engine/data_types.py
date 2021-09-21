from pydantic import BaseModel, root_validator
from typing import Union, List, Optional

#Datatype invarient: Every field of this model uniquely identifies a paper
class PaperID(BaseModel):
    doi: Optional[str] = None
    pubmed_id: Optional[str] = None
    scopus_id: Optional[str] = None
    @root_validator(allow_reuse=True)
    def one_or_more_selected(cls, values):
        selected_ids = []
        for id_name, id_value in values.items():
            if id_value is not None:
                selected_ids.append(id_value)
        if len(selected_ids)==0:
            raise ValueError('No ids selected')
        return values

class PaperData(BaseModel):
    paper_id: PaperID
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
