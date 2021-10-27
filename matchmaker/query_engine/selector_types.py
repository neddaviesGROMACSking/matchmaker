from typing import Union
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union
from typing_extensions import get_args, get_origin
from matchmaker.query_engine.data_types import (
    AuthorData,
    BaseAuthorData,
    BaseInstitutionData,
    BasePaperData,
    InstitutionData,
    PaperData,
)
from matchmaker.query_engine.id_types import PaperID, PaperIDSelector
from pydantic import BaseModel, create_model
from copy import copy
SelectorDict = Dict[str, Union[bool, 'SelectorDict']]
Selector = TypeVar('Selector', bound = BaseModel)

class BaseSelector(Generic[Selector], BaseModel):
    def __contains__(self, item: Selector):
        def s_dict1_in_s_dict2(dict1: SelectorDict, dict2: SelectorDict) -> bool:
            def check_whole_dict_is_value(s_dict: SelectorDict, value: bool):
                for k, v in s_dict.items():
                    if isinstance(v, bool):
                        if v != value:
                            return False
                    elif isinstance(v, dict):
                        inner_value = check_whole_dict_is_value(v, value)
                        if inner_value != value:
                            return False
                return True
            for k, self_v in dict2.items():
                item_v =  dict1[k]
                if self_v is True and item_v is True:
                    pass
                elif self_v is True and item_v is False:
                    pass
                elif self_v is False and item_v is True:
                    return False
                elif self_v is False and item_v is False:
                    pass
                elif self_v is True and isinstance(item_v, dict):
                    pass
                elif self_v is False and isinstance(item_v, dict):
                    item_v_is_false = check_whole_dict_is_value(item_v, False)
                    if not item_v_is_false:
                        return False
                elif isinstance(self_v, dict) and item_v is True:
                    self_v_is_true = check_whole_dict_is_value(self_v, True)
                    if not self_v_is_true:
                        return False
                elif isinstance(self_v, dict) and item_v is False:
                    pass
                elif isinstance(self_v, dict) and isinstance(item_v, dict):
                    item_in_self = s_dict1_in_s_dict2(item_v, self_v)
                    if not item_in_self:
                        return False
            return True
        self_dict = self.dict()
        item_dict = item.dict()

        return s_dict1_in_s_dict2(item_dict, self_dict)
    def generate_model(self, base_model: BaseModel, full_model: BaseModel) -> BaseModel:
        fields = full_model.__fields__
        selector_dict = self.dict()
        def make_model(model_name, selector_dict, base, fields):
            ellipsis_type = type(...)
            new_attrs: Dict[str, Tuple[type,Union[type, ellipsis_type]]] = {}
            for name, selector_value in selector_dict.items():
                if isinstance(selector_value, bool):
                    if selector_value:
                        model_field = fields[name]
                        field_type = model_field.outer_type_
                        if model_field.required:
                            field_default = ...
                        else:
                            field_default = model_field.default
                        new_attrs[name] = (field_type, field_default)
                elif isinstance(selector_value, dict):
                    model_field = fields[name]
                    sub_model_fields = model_field.type_.__fields__
                    base_model = model_field.type_.mro()[1] # TODO Find a better way to obtain - need super class
                    sub_model_name = model_field.type_.__name__
                    if model_field.required:
                        field_default = ...
                    else:
                        field_default = model_field.default

                    sub_model = make_model(sub_model_name, selector_value, base_model, sub_model_fields)
                    type_origin = get_origin(model_field.outer_type_)
                    if type_origin is None:
                        new_field_type = sub_model
                    else:
                        new_field_type = type_origin[sub_model]
                    new_attrs[name] = (new_field_type, field_default)
                else:
                    raise TypeError('Unsupported type in selector')
            return create_model(model_name, **new_attrs, __base__ = base)
        
        model = make_model('PaperData', selector_dict, base_model, fields)
        return model



class InstitutionDataSelector(BaseSelector['InstitutionDataSelector']):
    name: bool = False
    id: bool = False
    processed: bool = False
    paper_count: bool = False
    name_variants: bool = False

    def generate_model(self) -> BaseInstitutionData:
        return super().generate_model(BaseInstitutionData, InstitutionData)

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
    subjects: bool = False
    institution_current: Union[bool, InstitutionDataSelector] = False
    other_institutions: Union[bool, InstitutionDataSelector] = False
    paper_count: bool = False
    paper_ids: Union[bool, PaperIDSelector] = False

    def generate_model(self) -> BaseAuthorData:
        return super().generate_model(BaseAuthorData, AuthorData)

class TopicSelector(BaseModel):
    descriptor: bool = False
    qualifier: bool = False

class SubPaperDataSelector(BaseModel):
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

class PaperDataSelector(SubPaperDataSelector, BaseSelector['PaperDataSelector']):
    references: Union[bool, SubPaperDataSelector] = False
    cited_by: Union[bool, SubPaperDataSelector] = False

    def generate_model(self) -> BasePaperData:
        return super().generate_model(BasePaperData, PaperData)
