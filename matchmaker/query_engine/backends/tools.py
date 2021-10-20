import pdb
from typing import Dict, Union, List
DictStructure = Dict[str, Union[str, 'ListStructure', 'DictStructure']]
ListStructure = List[Union[str, 'ListStructure', 'DictStructure']]
def replace_dict_tag(dict_structure: DictStructure, old_value: str, new_value: str):
    def replace_list_tag(list_structure: ListStructure, old_value: str, new_value: str):
        new_list_structure = []
        for i in list_structure:
            if isinstance(i, dict):
                new_i = replace_dict_tag(i, old_value, new_value)
            elif isinstance(i, list):
                new_i = replace_list_tag(i, old_value, new_value)
            else:
                new_i = i
            new_list_structure.append(new_i)
        return new_list_structure
    new_dict_structure = {}
    for k, v in dict_structure.items():
        if k == 'tag':
            if isinstance(v, str):
                if v == old_value:
                    new_v = new_value
                else:
                    new_v = v
            else:
                raise ValueError('invalid tag')
            new_dict_structure[k] = new_v
        else:
            if isinstance(v, dict):
                new_v = replace_dict_tag(v, old_value, new_value)
            elif isinstance(v, list):
                new_v = replace_list_tag(v, old_value, new_value)
            else:
                new_v = v
            new_dict_structure[k] = new_v
    return new_dict_structure

def replace_dict_tags(dict_structure, **tags):
    current_dict_structure = dict_structure
    for new_value, old_value in tags.items():
        current_dict_structure = replace_dict_tag(current_dict_structure, old_value, new_value)
    return current_dict_structure