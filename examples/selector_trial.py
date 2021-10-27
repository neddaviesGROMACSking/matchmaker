
from pydantic import BaseModel
from typing import Dict, Union
import pdb
SelectorDict = Dict[str, Union[bool, 'SelectorDict']]

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


class Selector(BaseModel):
    class Sub(BaseModel):
        test:bool
        new:bool
    sub: Union[bool, Sub]
    name: bool
    auth_id: bool
    def __contains__(self, item: 'Selector'):
        self_dict = self.dict()
        item_dict = item.dict()

        return s_dict1_in_s_dict2(item_dict, self_dict)


selected = Selector.parse_obj({
    'sub': {
        'test': True,
        'new': False
    }, 
    'name': False, 
    'auth_id': True
})
complete = Selector.parse_obj({
    'sub': {
        'test': True,
        'new': True
    }, 
    'name': False, 
    'auth_id': True
})
#print(selected in complete)