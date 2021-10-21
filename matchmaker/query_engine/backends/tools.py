import pdb
from typing import Dict, Union, List
DictStructure = Dict[str, Union[str, 'ListStructure', 'DictStructure']]
ListStructure = List[Union[str, 'ListStructure', 'DictStructure']]


def execute_callback_on_tag(dict_structure: DictStructure, search_value: str, callback):
    def replace_list_tag(list_structure: ListStructure, search_value: str, callback):
        new_list_structure = []
        for i in list_structure:
            if isinstance(i, dict):
                new_i = execute_callback_on_tag(i, search_value, callback)
            elif isinstance(i, list):
                new_i = replace_list_tag(i, search_value, callback)
            else:
                new_i = i
            new_list_structure.append(new_i)
        return new_list_structure

    if 'tag' in dict_structure and dict_structure['tag'] == search_value:
        new_dict_structure = callback(dict_structure)
    else:
        new_dict_structure = {}
        for k, v in dict_structure.items():
            if isinstance(v, dict):
                new_v = execute_callback_on_tag(v, search_value, callback)
            elif isinstance(v, list):
                new_v = replace_list_tag(v, search_value, callback)
            else:
                new_v = v
            new_dict_structure[k] = new_v
    return new_dict_structure


def replace_dict_tags(dict_structure, **tags):
    def construct_tag_replace_callback(new_value):
        def tag_replace_callback(dict_structure):
            dict_structure['tag'] = new_value
            return dict_structure
        return tag_replace_callback

    current_dict_structure = dict_structure
    for new_value, old_value in tags.items():
        callback = construct_tag_replace_callback(new_value)
        current_dict_structure = execute_callback_on_tag(current_dict_structure, old_value, callback)
    return current_dict_structure

