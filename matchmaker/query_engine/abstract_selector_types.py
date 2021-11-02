from typing import Callable, Union
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union
import typing
from typing_extensions import get_origin, get_args
from pydantic import BaseModel, create_model
from pydantic.fields import ModelField
from copy import copy
import pdb

def extract_sub_model(model_field: ModelField) -> Tuple[BaseModel, str, Callable[[BaseModel], type]]:
    """
    Takes a model field, returns:
    Submodel type
    Submodel name
    Function that takes submodel type and wraps in outer types
    """
    EllipsisType = type(...)
    SomethingType = Union[EllipsisType, type, Tuple[type, List['SomethingType']]]
    def get_something_type(tp: type) -> Tuple[SomethingType, BaseModel]:
        args = list(get_args(tp))
        origin = get_origin(tp)
        if args == [] or origin is None:
            if hasattr(tp, '__fields__'):
                return ..., tp
            else:
                return tp, None
        else:
            possible_models = []
            new_args = []
            for arg in args:
                smtp, model = get_something_type(arg)
                if model is not None:
                    possible_models += [model]
                new_args += [smtp]
            if len(possible_models)>1:
                raise ValueError('More than one base model found')
            elif len(possible_models) == 1:
                relevant_model = possible_models[0]
            else:
                relevant_model = None
            return (origin, new_args), relevant_model
    
    def construct_func_type_wrapper_from_smtp(smtp: SomethingType):
        def func_type_wrapper(submodel: BaseModel):                
            def func_type_inner(current_smtp: SomethingType) -> type:
                if isinstance(current_smtp, EllipsisType):
                    return submodel
                elif isinstance(current_smtp, tuple):
                    origin = current_smtp[0]
                    args = current_smtp[1]
                    new_args = []
                    for arg in args:
                        new_arg = func_type_inner(arg)
                        new_args += [new_arg]
                    return origin[tuple(new_args)] #type: ignore - No way to verify origin has this method
                else:
                    return current_smtp
            return func_type_inner(smtp)
        return func_type_wrapper

    smth_type, submodel_type = get_something_type(model_field.outer_type_)
    submodel_name = submodel_type.__name__
    func_type_wrapper = construct_func_type_wrapper_from_smtp(smth_type)

    return submodel_type, submodel_name, func_type_wrapper


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

    def get_values_overselected(self, selector: Selector) -> List[List[str]]:
        # Potentially make contain depend on this method, 
        # returning True if it raises ValuesNotOverselected
        def get_overselects(current_path: List[str], dict1: SelectorDict, dict2: SelectorDict) -> List[List[str]]:
            def get_paths_from_dict_matching_value(current_path: List[str], dict_to_extract: SelectorDict, value: bool) -> List[List[str]]:
                matches = []
                new_current_path = copy(current_path)
                for k, v in dict_to_extract.items():
                    new_current_path += [k]
                    if isinstance(v, bool) and v == value:
                        matches += [new_current_path]
                    elif isinstance(v, dict):
                        matches += get_paths_from_dict_matching_value(new_current_path, v, value)
                    new_current_path = new_current_path[0:-1]
                return matches

            total_overselects = []
            new_current_path = copy(current_path)
            for k, self_v in dict2.items():
                new_current_path += [k]
                item_v = dict1[k]
                overselects = []
                if self_v is False and item_v is True:
                    overselects = [new_current_path]
                elif self_v is False and isinstance(item_v, dict):
                    overselects = get_paths_from_dict_matching_value(new_current_path, item_v, True)

                elif isinstance(self_v, dict) and item_v is True:
                    overselects = get_paths_from_dict_matching_value(new_current_path, self_v, False)

                elif isinstance(self_v, dict) and isinstance(item_v, dict):
                    overselects = get_overselects(new_current_path, item_v, self_v)

                else:
                    overselects = []
                total_overselects += copy(overselects)
                new_current_path = new_current_path[0:-1]
            return total_overselects
        self_dict = self.dict()
        item_dict = selector.dict()
        overselects = get_overselects([], item_dict, self_dict)
        return overselects
    @classmethod
    def generate_subset_selector(cls, selector: Selector, fields_available: Selector):
        # Produce a version of selector limited to only the fields available

        def make_subset_selector_dict(selector_dict: SelectorDict, available_dict: SelectorDict):
            subset_selector_dict = {}
            for selector_k, selector_v in selector_dict.items():
                available_v = available_dict[selector_k]

                if selector_v is True and available_v is True:
                    subset_selector_dict[selector_k] = selector_v
                elif selector_v is True and available_v is False:
                    pass
                elif selector_v is False and available_v is True:
                    pass
                elif selector_v is False and available_v is False:
                    pass
                elif selector_v is True and isinstance(available_v, dict):
                    subset_selector_dict[selector_k] = available_v
                elif selector_v is False and isinstance(available_v, dict):
                    pass
                elif isinstance(selector_v, dict) and available_v is True:
                    subset_selector_dict[selector_k] = selector_v
                elif isinstance(selector_v, dict) and available_v is False:
                    pass
                elif isinstance(selector_v, dict) and isinstance(available_v, dict):
                    subset_selector_dict[selector_k] = make_subset_selector_dict(selector_v, available_v)
            return subset_selector_dict

        selector_dict = selector.dict()
        fields_available_dict = fields_available.dict()   
        subset_selector_dict = make_subset_selector_dict(selector_dict, fields_available_dict)
        return cls.parse_obj(subset_selector_dict)  

    def generate_model(self, base_model: BaseModel, full_model: BaseModel, model_mapper: Dict[str, BaseModel] = {}) -> BaseModel:
        def make_model(model_name, selector_dict, base, fields):
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
            ellipsis_type = type(...)
            new_attrs: Dict[str, Tuple[type,Union[type, ellipsis_type]]] = {}
            for name, selector_value in selector_dict.items():
                if isinstance(selector_value, bool) and selector_value:
                    model_field = fields[name]
                    field_type = model_field.outer_type_
                    if model_field.required:
                        field_default = ...
                    else:
                        field_default = model_field.default
                    new_attrs[name] = (field_type, field_default)
                elif isinstance(selector_value, dict) and not check_whole_dict_is_value(selector_value, False):
                    model_field = fields[name]
                    submodel_type, sub_model_name, submodel_type_func = extract_sub_model(model_field)

                    sub_model_fields = submodel_type.__fields__
        
                    if name in model_mapper:
                        base_model = model_mapper[name]
                    else:
                        base_model = BaseModel

                    #base_model = model_field.type_.mro()[1] # TODO Find a better way to obtain - need super class
                    if model_field.required:
                        field_default = ...
                    else:
                        field_default = model_field.default

                    sub_model = make_model(sub_model_name, selector_value, base_model, sub_model_fields)

                    new_field_type = submodel_type_func(sub_model)
                    new_attrs[name] = (new_field_type, field_default)
            return create_model(model_name, **new_attrs, __base__ = base)
        fields = full_model.__fields__
        selector_dict = self.dict()
        model = make_model(base_model.__name__, selector_dict, base_model, fields)
        return model



