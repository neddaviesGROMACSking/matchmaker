import pdb
from typing import Dict, Union, List
DictStructure = Dict[str, Union[str, 'ListStructure', 'DictStructure']]
ListStructure = List[Union[str, 'ListStructure', 'DictStructure']]

def execute_callback_on_tag_condition(
    dict_structure: DictStructure, tag_condition, callback
):
    def replace_list_tag(list_structure: ListStructure, tag_condition, callback):
        new_list_structure = []
        for i in list_structure:
            if isinstance(i, dict):
                new_i = execute_callback_on_tag_condition(i, tag_condition, callback)
            elif isinstance(i, list):
                new_i = replace_list_tag(i, tag_condition, callback)
            else:
                new_i = i
            new_list_structure.append(new_i)
        return new_list_structure

    if 'tag' in dict_structure and tag_condition(dict_structure['tag']):
        new_dict_structure = callback(dict_structure)
    else:
        new_dict_structure = {}
        for k, v in dict_structure.items():
            if isinstance(v, dict):
                new_v = execute_callback_on_tag_condition(v, tag_condition, callback)
            elif isinstance(v, list):
                new_v = replace_list_tag(v, tag_condition, callback)
            else:
                new_v = v
            new_dict_structure[k] = new_v
    return new_dict_structure

def execute_callback_on_tag(dict_structure: DictStructure, search_value: str, callback):
    def tag_condition(tag: str):
        return tag == search_value
    return execute_callback_on_tag_condition(dict_structure, tag_condition, callback)


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


def replace_ids(dict_structure):
    def id_callback(dict_structure):
        pdb.set_trace()
    return execute_callback_on_tag(dict_structure, 'id', id_callback)

def get_available_model_tags(model):
    tags = []
    for arg in model.__fields__['__root__'].type_.__args__:
        tag = arg.__fields__['tag'].default
        if tag not in tags:
            tags.append(tag)
        if 'operator' in arg.__fields__:
            for sub_arg in arg.__fields__['operator'].type_.__args__:
                sub_tag = sub_arg.__fields__['tag'].default
                if sub_tag not in tags:
                    tags.append(sub_tag)
    return tags

class TagNotFound(ValueError):
    def __init__(self, tag, model_tags) -> None:
        self.tag = tag
        self.model_tags = model_tags
        msg = f'Tag: {tag} not found in {model_tags}'
        super().__init__(msg)


def check_model_tags(model_tags: List[str], dict_structure: DictStructure):
    def tag_not_found_callback(dict_structure):
        raise TagNotFound(dict_structure['tag'], model_tags)
    def tag_condition(tag:str) -> bool:
        return tag not in model_tags
    execute_callback_on_tag_condition(dict_structure, tag_condition, tag_not_found_callback)
