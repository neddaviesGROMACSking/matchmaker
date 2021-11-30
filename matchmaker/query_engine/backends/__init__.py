from asyncio import Future, coroutine, get_running_loop
import asyncio
from dataclasses import dataclass
import time
from typing import Awaitable, Callable, Dict, Generic, Optional, Tuple, TypeVar
import uuid

from aiohttp import ClientSession, TCPConnector
from matchmaker.query_engine.slightly_less_abstract import (
    AbstractNativeQuery,
    SlightlyLessAbstractQueryEngine,
)
from matchmaker.query_engine.types.data import AuthorData, InstitutionData, PaperData
from matchmaker.query_engine.types.query import (
    AuthorSearchQuery,
    InstitutionSearchQuery,
    PaperSearchQuery,
)
import warnings

MetadataType = Dict[str, Tuple[int, Optional[int]]]


class RateLimiter:
    bunch_start: Optional[float]
    max_requests_per_second: int
    requests_made: int
    def __init__(self, *args, max_requests_per_second = 9, **kwargs):
        self.max_requests_per_second = max_requests_per_second
        self.bunch_start= None
        self.requests_made = 0
        super().__init__(*args, **kwargs)
    
    async def rate_limit(self):
        current_time = time.time()
        if self.bunch_start is None:
            self.bunch_start = current_time
            self.requests_made = 1
        else:
            elapsed = current_time - self.bunch_start
            if elapsed < (1/self.max_requests_per_second):
                if self.requests_made >= 1:
                    await asyncio.sleep(1/self.max_requests_per_second)
                    await self.rate_limit()
                else:
                    self.requests_made += 1
            else:
                self.bunch_start = current_time
                self.requests_made = 1


with warnings.catch_warnings():
    warnings.filterwarnings("ignore",category=DeprecationWarning)
    class NewAsyncClient(ClientSession):
        rate_limiter: RateLimiter

        def __init__(self, rate_limiter: RateLimiter = RateLimiter(), *args, **kwargs):
            self.rate_limiter = rate_limiter
            super().__init__(*args, **kwargs)
        async def get(self, *args, **kwargs):
            await self.rate_limiter.rate_limit()
            output = await super().get(*args, **kwargs)
            print(int(dict(output.raw_headers)[b'X-RateLimit-Remaining']))
            return output

        async def post(self, *args, **kwargs):
            await self.rate_limiter.rate_limit()
            output = await super().post(*args, **kwargs)
            print(int(dict(output.raw_headers)[b'X-RateLimit-Remaining']))
            return output
    
NativeData = TypeVar('NativeData')

class BaseNativeQuery(Generic[NativeData], AbstractNativeQuery):
    coroutine_function: Callable[[NewAsyncClient], Awaitable[NativeData]]
    _get_metadata: Callable[[], Awaitable[MetadataType]]
    _metadata: Optional[MetadataType]
    def __init__(
        self, 
        coroutine_function: Callable[[NewAsyncClient], Awaitable[NativeData]], 
        get_metadata: Callable[[], Awaitable[MetadataType]]
    ) -> None:
        self.coroutine_function = coroutine_function
        self._get_metadata = get_metadata
        self._metadata = None
    async def metadata(self):
        return await self._get_metadata()
    async def count_api_calls(self):
        if self._metadata is None:
            self._metadata = await self.metadata()
        return sum(self._metadata.values())
    async def count_api_calls_by_method(self, method: str):
        if self._metadata is None:
            self._metadata = await self.metadata()
        return self._metadata[method]

Query = TypeVar('Query')
Data = TypeVar('Data')


class BaseBackendQueryEngine(
    Generic[Query, NativeData, Data], 
    SlightlyLessAbstractQueryEngine[Query, BaseNativeQuery[NativeData], NativeData, Data]
):
    def __init__(self, rate_limiter = RateLimiter(), *args, **kwargs):
        self.rate_limiter = rate_limiter
        super().__init__(*args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: Query, 
        client: NewAsyncClient
    ) -> Tuple[Callable[[NewAsyncClient], Awaitable[NativeData]], Callable[[], Awaitable[MetadataType]]]:
        raise NotImplementedError('This method is required for query_to_native')
    async def _query_to_native(self, query: Query) -> BaseNativeQuery[NativeData]:
        connector = TCPConnector(force_close=True)
        async with NewAsyncClient(connector = connector, rate_limiter = self.rate_limiter) as client:
            coro = self._query_to_awaitable(query,  client)
            coroutine_function, get_metadata = await coro
        return BaseNativeQuery(coroutine_function, get_metadata)

    async def _run_native_query(self, query: BaseNativeQuery[NativeData]) -> NativeData:
        connector = TCPConnector(force_close=True)
        async with NewAsyncClient(connector = connector, rate_limiter = self.rate_limiter) as client:
            results = await query.coroutine_function(client)
        return results
    
    async def _post_process(self, query: Query, data: NativeData) -> Data:
        raise NotImplementedError('Calling method on abstract base class')

    async def __call__(self, query: Query) -> Data:
        nd = await self._run_native_query(await self._query_to_native(query))
        return await self._post_process(query, nd)
    
    #Put post process as no op


class BasePaperSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[PaperSearchQuery, NativeData, PaperData]
):
    pass


class BaseAuthorSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[AuthorSearchQuery, NativeData, AuthorData]
):
    pass

class BaseInstitutionSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[InstitutionSearchQuery, NativeData, InstitutionData]
):
    pass
