from typing import Union
from pydantic import BaseModel, PrivateAttr
from typing import Union, List, Optional, Tuple, Dict, Any
from matchmaker.query_engine.id_types import PaperID

class Inverter(BaseModel):
    _arg_store: Any = PrivateAttr()
    _kwarg_store: Any = PrivateAttr()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._arg_store = args
        self._kwarg_store = kwargs
    @classmethod
    def make_model(cls, model):
        return cls(*model._arg_store, **model._kwarg_store)
    def __invert__(self):
        def invert_fields(field, value):
            if hasattr(field, '__fields__'):
                for field in field.__fields__.values():
                    field.default = value
                    if hasattr(field.type_, '__args__'):
                        for i in field.type_.__args__:
                            invert_fields(i, value)
        invert_fields(self, True)
        new_obj = self.make_model(self)
        invert_fields(self, False)
        return new_obj

class AuthorDataSelector(BaseModel):
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
    paper_ids: Optional[List[PaperID]] = []


class TopicSelector(BaseModel):
    descriptor: Optional[str]
    qualifier: Optional[str]

class SubPaperDataSelector(BaseModel):
    paper_id: PaperID
    title: bool = False
    authors: Union[bool, AuthorDataSelector] = False
    year: bool = False
    source_title: bool = False
    source_title_abr: bool = False
    abstract: bool = False
    institutions: bool = False
    keywords: bool = False
    topics: Union[bool, TopicSelector] = False


class PaperDataSelector(Inverter, SubPaperDataSelector):
    references: Union[bool, SubPaperDataSelector] = True
    cited_by: Union[bool, SubPaperDataSelector] = True
