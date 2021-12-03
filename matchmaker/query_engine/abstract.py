from typing import Generic, TypeVar


Query = TypeVar('Query')
Data = TypeVar('Data')


class AbstractQueryEngine(Generic[Query, Data]):
    def __call__(self, query: Query) -> Data:
        raise NotImplementedError('Calling method on abstract base class')
