from typing import Union
from pydantic import BaseModel, PrivateAttr
from typing import Union, List, Optional, Tuple, Dict, Any, TypeVar, Generic
from matchmaker.query_engine.id_types import PaperID, PaperIDSelector

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

class InstitutionDataSelector(BaseSelector['InstitutionDataSelector']):
    name: bool = False
    id: bool = False
    processed: bool = False
    paper_count: bool = False
    name_variants: bool = False

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
    references: Union[bool, SubPaperDataSelector] = True
    cited_by: Union[bool, SubPaperDataSelector] = True

