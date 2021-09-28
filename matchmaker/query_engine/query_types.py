from pydantic import BaseModel, Field
from pydantic.generics import GenericModel
from typing import Annotated, Generic, List, Literal, Type, TypeVar, Union
from collections.abc import Container
from numbers import Real
from matchmaker.query_engine.id_types import PaperID
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


class Journal(BaseModel):
    tag: Literal['journal'] = 'journal'
    operator: StringPredicate


class Abstract(BaseModel):
    tag: Literal['abstract'] = 'abstract'
    operator: StringPredicate


class Institution(BaseModel):
    tag: Literal['institution'] = 'institution'
    operator: StringPredicate


class Keyword(BaseModel):
    tag: Literal['keyword'] = 'keyword'
    operator: StringPredicate


class Year(BaseModel):
    tag: Literal['year'] = 'year'
    operator: IntPredicate


# mypy currently can't handle recursive types:
# https://github.com/python/mypy/issues/731
and_int = And['PaperSearchQuery']
or_int = Or['PaperSearchQuery']

class PaperSearchQuery(BaseModel):
    __root__: Annotated[  # type: ignore[misc]
    Union[
        and_int,  # type: ignore[misc]
        or_int,  # type: ignore[misc]
        Title,
        AuthorName,
        Journal,
        Abstract,
        Institution,
        Keyword,
        Year],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()
PaperSearchQuery.update_forward_refs()


class Name(BaseModel):
    tag: Literal['name'] = 'name'
    operator: StringPredicate


# mypy currently can't handle recursive types:
# https://github.com/python/mypy/issues/731
AuthorSearchQuery = Annotated[  # type: ignore[misc]
    Union[
        And['AuthorSearchQuery'],  # type: ignore[misc]
        Or['AuthorSearchQuery'],  # type: ignore[misc]
        Name,
        Institution],
    Field(discriminator='tag')]


And['AuthorSearchQuery'].update_forward_refs()
Or['AuthorSearchQuery'].update_forward_refs()
