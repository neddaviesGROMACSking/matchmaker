from pydantic import BaseModel
from typing import Generic, Union, Dict, TypeVar
from matchmaker.query_engine.abstract_selector_types import BaseSelector


SelectorType = TypeVar('SelectorType', bound = BaseSelector)

class BaseData(BaseModel, Generic[SelectorType]):
    @classmethod
    def generate_model_from_selector(
        cls, 
        definition: BaseModel, 
        selector: Union[bool, SelectorType], 
        model_mapper: Dict[str, BaseModel] = {}):
        if isinstance(selector, bool):
            if selector:
                return type(cls.__name__, (definition, cls), {}) 
            else:
                return cls
        else:
            return selector.generate_model(cls, definition, model_mapper)
