from collections.abc import Container
from numbers import Real
from typing import Annotated, Generic, List, Literal, Type, TypeVar, Union

from matchmaker.query_engine.types.data import PaperID, AuthorID, InstitutionID
from matchmaker.query_engine.types.selector import (
    AuthorDataAllSelected,
    AuthorDataSelector,
    InstitutionDataAllSelected,
    InstitutionDataSelector,
    PaperDataSelector,
    PaperDataAllSelected
)
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel
QueryType = TypeVar('QueryType')  # TODO: restrict to query types only


class And(GenericModel, Generic[QueryType]):
    tag: Literal['and'] = 'and'
    fields_: List[QueryType]


class Or(GenericModel, Generic[QueryType]):
    tag: Literal['or'] = 'or'
    fields_: List[QueryType]


Constant = TypeVar('Constant')  # TODO: replace with ABC for __eq__


class EqualPredicate(GenericModel, Generic[Constant]):
    tag: Literal['equal'] = 'equal'
    value: Constant


ContainerType = TypeVar('ContainerType', bound=Type[Container])


class InPredicate(GenericModel, Generic[ContainerType]):
    tag: Literal['in'] = 'in'
    value: ContainerType


RealType = TypeVar('RealType', bound=Type[Real])


class LTPredicate(GenericModel, Generic[RealType]):
    tag: Literal['lt'] = 'lt'
    value: RealType


class GTPredicate(GenericModel, Generic[RealType]):
    tag: Literal['gt'] = 'gt'
    value: RealType


class RangePredicate(GenericModel, Generic[RealType]):
    tag: Literal['range'] = 'range'
    lower_bound: RealType
    upper_bound: RealType


# float isn't a subclass of typing.Real...?
FloatPredicate = Union[
        EqualPredicate[float], LTPredicate[float],  # type: ignore
        GTPredicate[float], RangePredicate[float]]  # type: ignore

# int isn't a subclass of typing.Real...?
IntPredicate = Union[
        EqualPredicate[int], LTPredicate[int],  # type: ignore
        GTPredicate[int], RangePredicate[int]]  # type: ignore

# str has __contains__ but isn't a subclass of typing.Container...?
StringPredicate = Union[EqualPredicate[str], InPredicate[str]]  # type: ignore





class Title(BaseModel):
    tag: Literal['title'] = 'title'
    operator: StringPredicate


class AuthorName(BaseModel):
    tag: Literal['author'] = 'author'
    operator: StringPredicate

AuthorIDAllActive = AuthorID.generate_model_from_selector()
class AuthorIDHigh(BaseModel):
    tag: Literal['authorid'] = 'authorid'
    operator: EqualPredicate[AuthorIDAllActive]

class Journal(BaseModel):
    tag: Literal['journal'] = 'journal'
    operator: StringPredicate


class Abstract(BaseModel):
    tag: Literal['abstract'] = 'abstract'
    operator: StringPredicate


class Institution(BaseModel):
    tag: Literal['institution'] = 'institution'
    operator: StringPredicate

InstitutionIDAllActive = InstitutionID.generate_model_from_selector()
class InstitutionIDHigh(BaseModel):
    tag: Literal['institutionid'] = 'institutionid'
    operator: EqualPredicate[InstitutionIDAllActive]

class Keyword(BaseModel):
    tag: Literal['keyword'] = 'keyword'
    operator: StringPredicate


class Year(BaseModel):
    tag: Literal['year'] = 'year'
    operator: IntPredicate

class Topic(BaseModel):
    tag: Literal['topic'] = 'topic'
    operator: StringPredicate

PaperIDAllActive = PaperID.generate_model_from_selector()
class PaperIDHigh(BaseModel):
    tag: Literal['id'] = 'id'
    operator: EqualPredicate[PaperIDAllActive]

and_int = And['PaperSearchQueryInner']
or_int = Or['PaperSearchQueryInner']

class PaperSearchQueryInner(BaseModel):
    __root__: Annotated[
    Union[
        and_int,
        or_int,
        PaperIDHigh,
        Title,
        AuthorName,
        AuthorIDHigh,
        Journal,
        Abstract,
        Institution,
        InstitutionIDHigh,
        Keyword,
        Year,
        Topic],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()
PaperSearchQueryInner.update_forward_refs()

class PaperSearchQuery(BaseModel):
    query: PaperSearchQueryInner
    selector: PaperDataSelector = PaperDataAllSelected

and_int = And['AuthorSearchQueryInner']
or_int = Or['AuthorSearchQueryInner']

class AuthorSearchQueryInner(BaseModel):
    __root__: Annotated[  
    Union[
        and_int,  
        or_int,  
        AuthorName,
        AuthorIDHigh,
        Institution,
        InstitutionIDHigh,
        Year,
        Title,
        Abstract,
        Keyword,
        Topic,
    ],
    Field(discriminator='tag')]


and_int.update_forward_refs()
or_int.update_forward_refs()
AuthorSearchQueryInner.update_forward_refs()

class AuthorSearchQuery(BaseModel):
    query: AuthorSearchQueryInner
    selector: AuthorDataSelector = AuthorDataAllSelected


and_int = And['InstitutionSearchQueryInner']
or_int = Or['InstitutionSearchQueryInner']

class InstitutionSearchQueryInner(BaseModel):
    __root__: Annotated[
    Union[
        and_int,  
        or_int,
        Institution,
        InstitutionIDHigh
    ],
    Field(discriminator='tag')]
    
and_int.update_forward_refs()
or_int.update_forward_refs()
InstitutionSearchQueryInner.update_forward_refs()

class InstitutionSearchQuery(BaseModel):
    query: InstitutionSearchQueryInner
    selector: InstitutionDataSelector = InstitutionDataAllSelected
