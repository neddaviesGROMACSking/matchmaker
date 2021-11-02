from typing import List

class QueryNotSupportedError(ValueError):
    def __init__(self, overselected_fields: List[List[str]]) -> None:
        new_fields = '\n'.join([' -> '.join(i) for i in overselected_fields])
        msg = f"Unsupported fields selected: \n{new_fields}"
        super().__init__(msg)

class SearchNotPossible(ValueError):
    pass