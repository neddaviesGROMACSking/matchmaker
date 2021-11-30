from asyncio import Future, coroutine, get_running_loop
import asyncio
from dataclasses import dataclass
import time
from typing import (
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Tuple,
    TypeVar,
)
import uuid
import warnings

from aiohttp import ClientSession, TCPConnector
from matchmaker.query_engine.backends import (
    BaseBackendQueryEngine,
    BaseNativeQuery,
    BasePaperSearchQueryEngine,
    BaseAuthorSearchQueryEngine,
    BaseInstitutionSearchQueryEngine,
    GetMetadata
)
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

class WebNativeQuery(
    Generic[NativeData], 
    BaseNativeQuery[
        NativeData, 
        Callable[[NewAsyncClient], Awaitable[NativeData]]
    ]
):
    pass


Query = TypeVar('Query')
ProcessedData = TypeVar('ProcessedData', bound = AsyncIterator)
NativeQuery = TypeVar('NativeQuery', bound = WebNativeQuery)
DataElement = TypeVar('DataElement')

class WebQueryEngine(
    Generic[Query, NativeQuery, NativeData, ProcessedData, DataElement], 
    BaseBackendQueryEngine[Query, NativeQuery, NativeData, ProcessedData, DataElement]
):
    def __init__(self, rate_limiter = RateLimiter(), *args, **kwargs):
        self.rate_limiter = rate_limiter
        super().__init__(*args, **kwargs)
    
    async def _query_to_awaitable(
        self, 
        query: Query, 
        client: NewAsyncClient
    ) -> Tuple[Callable[[NewAsyncClient], Awaitable[NativeData]], GetMetadata]:
        raise NotImplementedError('This method is required for query_to_native')
    async def _query_to_native(self, query: Query) -> WebNativeQuery[NativeData]:
        connector = TCPConnector(force_close=True)
        async with NewAsyncClient(connector = connector, rate_limiter = self.rate_limiter) as client:
            get_data, get_metadata = await self._query_to_awaitable(query, client)            
        return WebNativeQuery[NativeData](get_data, get_metadata)

    async def _run_native_query(self, query: WebNativeQuery[NativeData]) -> NativeData:
        connector = TCPConnector(force_close=True)
        async with NewAsyncClient(connector = connector, rate_limiter = self.rate_limiter) as client:
            results: NativeData = await query.coroutine_function(client)
        return results

class WebPaperSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData],
    BasePaperSearchQueryEngine[NativeQuery, NativeData, ProcessedData],
    WebQueryEngine[PaperSearchQuery, NativeQuery, NativeData, ProcessedData, PaperData],

):
    pass

class WebAuthorSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData],
    BaseAuthorSearchQueryEngine[NativeQuery, NativeData, ProcessedData],
    WebQueryEngine[AuthorSearchQuery, NativeQuery, NativeData, ProcessedData, AuthorData],
):
    pass

class WebInstitutionSearchQueryEngine(
    Generic[NativeQuery, NativeData, ProcessedData],
    BaseInstitutionSearchQueryEngine[NativeQuery, NativeData, ProcessedData],
    WebQueryEngine[InstitutionSearchQuery, NativeQuery, NativeData, ProcessedData, InstitutionData],
):
    pass
