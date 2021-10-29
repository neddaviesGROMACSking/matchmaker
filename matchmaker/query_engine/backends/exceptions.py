from typing import List

class QueryNotSupportedError(ValueError):
    def __init__(self, overselected_fields: List[str]) -> None:
        msg = "Unsupported fields selected: {overselected_fields}"
        super().__init__(msg)

