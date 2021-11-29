from typing import Callable, Union
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union
import typing
from typing_extensions import get_origin, get_args
from pydantic import BaseModel, create_model
from pydantic.fields import ModelField
from copy import copy
import pdb
from typing import Callable, Union
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union
import typing
from typing_extensions import get_origin, get_args
from pydantic import BaseModel, create_model
from pydantic.fields import ModelField
from copy import copy
import pdb
from type_reconstructor import extract_element


def extract_sub_model(model_field: ModelField) -> Tuple[BaseModel, str, Callable[[BaseModel], type]]:
    """
    Takes a model field, returns:
    Submodel type
    Submodel name
    Function that takes submodel type and wraps in outer types
    """
    
    def condition(tp: type) -> bool:
        return hasattr(tp, '__fields__')
    submodel_type, func_type_wrapper = extract_element(model_field.outer_type_, condition)
    submodel_name = submodel_type.__name__

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
                        if not inner_value:
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

    def any_of_fields(self, relevant_fields: Selector) -> bool:
        def any_of_fields_inner(selector_dict: SelectorDict, relevant_fields_dict: SelectorDict) -> bool:
            def check_any_of_dict_is_value(s_dict: SelectorDict, value: bool):
                for k, v in s_dict.items():
                    if isinstance(v, bool):
                        if v == value:
                            return True
                    elif isinstance(v, dict):
                        inner_value = check_any_of_dict_is_value(v, value)
                        if inner_value:
                            return True
                return False
            for k, self_v in selector_dict.items():
                item_v =  relevant_fields_dict[k]
                if self_v is True and item_v is True:
                    return True
                elif self_v is True and item_v is False:
                    pass
                elif self_v is False and item_v is True:
                    pass
                elif self_v is False and item_v is False:
                    pass
                elif self_v is True and isinstance(item_v, dict):
                    item_v_is_true = check_any_of_dict_is_value(item_v, True)
                    if item_v_is_true:
                        return True
                elif self_v is False and isinstance(item_v, dict):
                    pass
                elif isinstance(self_v, dict) and item_v is True:
                    self_v_is_true = check_any_of_dict_is_value(self_v, True)
                    if self_v_is_true:
                        return True
                elif isinstance(self_v, dict) and item_v is False:
                    pass
                elif isinstance(self_v, dict) and isinstance(item_v, dict):
                    any_fields_selected = any_of_fields_inner(item_v, self_v)
                    if any_fields_selected:
                        return True
            return False
        self_dict = self.dict()
        relevant_fields_dict = relevant_fields.dict()
        return any_of_fields_inner(self_dict, relevant_fields_dict)
    
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
        # TODO Change this method name to "intersection" in accordance with set
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

    @classmethod
    def generate_superset_selector(cls, selector1: Selector, selector2: Selector):
        # TODO Change this method name to "union" in accordance with set
        def make_superset_selector_dict(dict1: SelectorDict, dict2: SelectorDict):
            superset_selector_dict = {}
            for dict1_k, dict1_v in dict1.items():
                dict2_v = dict2[dict1_k]

                if dict1_v is True and dict2_v is True:
                    superset_selector_dict[dict1_k] = dict1_v
                elif dict1_v is True and dict2_v is False:
                    superset_selector_dict[dict1_k] = dict1_v
                elif dict1_v is False and dict2_v is True:
                    superset_selector_dict[dict1_k] = dict2_v
                elif dict1_v is False and dict2_v is False:
                    pass
                elif dict1_v is True and isinstance(dict2_v, dict):
                    superset_selector_dict[dict1_k] = dict1_v
                elif dict1_v is False and isinstance(dict2_v, dict):
                    superset_selector_dict[dict1_k] = dict2_v
                elif isinstance(dict1_v, dict) and dict2_v is True:
                    superset_selector_dict[dict1_k] = dict2_v
                elif isinstance(dict1_v, dict) and dict2_v is False:
                    superset_selector_dict[dict1_k] = dict1_v
                elif isinstance(dict1_v, dict) and isinstance(dict2_v, dict):
                    superset_selector_dict[dict1_k] = make_superset_selector_dict(dict1_v, dict2_v)
            return superset_selector_dict
        selector1_dict = selector1.dict()
        selector2_dict = selector2.dict()   
        superset_selector_dict = make_superset_selector_dict(selector1_dict, selector2_dict)
        return cls.parse_obj(superset_selector_dict)  

    def __or__(self, other: Selector):
        return self.generate_superset_selector(self, other)

    def __and__(self, other: Selector):
        return self.generate_subset_selector(self, other)
    
    def generate_model(self, base_model: BaseModel, full_model: BaseModel, model_mapper: Dict[str, BaseModel] = {}) -> BaseModel:
        def make_model(model_name, selector_dict, base, fields):
            def check_whole_dict_is_value(s_dict: SelectorDict, value: bool):
                for k, v in s_dict.items():
                    if isinstance(v, bool):
                        if v != value:
                            return False
                    elif isinstance(v, dict):
                        inner_value = check_whole_dict_is_value(v, value)
                        if not inner_value:
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

# TODO Make all selectors inherit from BaseSelector

# Datatype invarient: Every field of this model uniquely identifies a paper
class PaperIDSelector(BaseSelector['PaperIDSelector']):
    doi: bool = False
    pubmed_id: bool = False
    scopus_id: bool = False

class AuthorIDSelector(BaseSelector['AuthorIDSelector']):
    pubmed_id: bool = False
    scopus_id: bool = False

class InstitutionIDSelector(BaseSelector['InstitutionIDSelector']):
    pubmed_id: bool = False
    scopus_id: bool = False

class InstitutionDataSelector(BaseSelector['InstitutionDataSelector']):
    name: bool = False
    id: Union[bool, InstitutionIDSelector] = False
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
    class NameSelector(BaseSelector['NameSelector']):
        surname: bool = False
        given_names: bool = False
        initials: bool = False
    class SubjectSelector(BaseSelector['SubjectSelector']):
        name: bool = False
        paper_count: bool = False
    preferred_name: Union[bool, NameSelector] = False
    id: Union[bool, AuthorIDSelector] = False
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



class TopicSelector(BaseSelector['TopicSelector']):
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
