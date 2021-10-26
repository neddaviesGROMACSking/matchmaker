from pydantic.error_wrappers import ValidationError

class QueryNotSupportedError(ValidationError):
    pass

