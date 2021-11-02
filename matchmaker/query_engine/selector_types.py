from typing import Callable, Union
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union
import typing
from typing_extensions import get_origin, get_args
from matchmaker.query_engine.id_types import PaperIDSelector
from matchmaker.query_engine.abstract_selector_types import BaseSelector
from pydantic import BaseModel, create_model
from pydantic.fields import ModelField
from copy import copy
import pdb

# TODO Make all selectors inherit from BaseSelector

class InstitutionDataSelector(BaseSelector['InstitutionDataSelector']):
    name: bool = False
    id: bool = False
    processed: bool = False
    paper_count: bool = False
    name_variants: bool = False

InstitutionDataAllSelected = InstitutionDataSelector(
    name = True,
    id = True,
    processed = True,
    paper_count = True,
    name_variants = True
)

class AuthorDataSelector(BaseSelector['AuthorDataSelector']):
    class NameSelector(BaseModel):
        surname: bool = False
        given_names: bool = False
        initials: bool = False
    class SubjectSelector(BaseModel):
        name: bool = False
        paper_count: bool = False
    preferred_name: Union[bool, NameSelector] = False
    id: bool = False
    name_variants: bool = False
    subjects: Union[bool, SubjectSelector] = False
    institution_current: Union[bool, InstitutionDataSelector] = False
    other_institutions: Union[bool, InstitutionDataSelector] = False
    paper_count: bool = False
    paper_ids: Union[bool, PaperIDSelector] = False

AuthorDataAllSelected = AuthorDataSelector(
    preferred_name = True,
    id = True,
    name_variants = True,
    subjects = True,
    institution_current = True,
    other_institutions = True,
    paper_count = True,
    paper_ids = True
)

class TopicSelector(BaseModel):
    descriptor: bool = False
    qualifier: bool = False

class SubPaperDataSelector(BaseSelector['SubPaperDataSelector']):
    paper_id: Union[bool, PaperIDSelector] = False
    title: bool = False
    authors: Union[bool, AuthorDataSelector] = False
    year: bool = False
    source_title: bool = False
    source_title_id: bool = False
    source_title_abr: bool = False
    abstract: bool = False
    institutions: Union[bool, InstitutionDataSelector]  = False
    keywords: bool = False
    topics: Union[bool, TopicSelector] = False

SubPaperDataAllSelected = SubPaperDataSelector(
    paper_id = True,
    title = True,
    authors = True,
    year = True,
    source_title = True,
    source_title_id = True,
    source_title_abr = True,
    abstract = True,
    institutions = True,
    keywords = True,
    topics = True
)

class PaperDataSelector(SubPaperDataSelector, BaseSelector['PaperDataSelector']):
    references: Union[bool, SubPaperDataSelector] = False
    cited_by: Union[bool, SubPaperDataSelector] = False

PaperDataAllSelected = PaperDataSelector(
    paper_id = True,
    title = True,
    authors = True,
    year = True,
    source_title = True,
    source_title_id = True,
    source_title_abr = True,
    abstract = True,
    institutions = True,
    keywords = True,
    topics = True,
    references = True,
    cited_by = True
)