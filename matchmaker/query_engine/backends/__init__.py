from dataclasses import dataclass
from asyncio import coroutine, Future, get_running_loop
from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.slightly_less_abstract import AbstractNativeQuery, SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.data_types import PaperData, AuthorData
from typing import Dict, TypeVar,Generic, Tuple, Callable, Awaitable, Optional

from aiohttp import ClientSession
import asyncio
import time

NativeData = TypeVar('NativeData')

import uuid

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
        

class NewAsyncClient(ClientSession):
    rate_limiter: RateLimiter
    number_of_tries:int

    def __init__(self, *args, rate_limiter: RateLimiter = RateLimiter(), number_of_tries=1000, **kwargs):
        self.rate_limiter = rate_limiter
        self.number_of_tries = number_of_tries
        super().__init__(*args, **kwargs)
    """
    async def get(self, *args, **kwargs):
        await self.rate_limiter.rate_limit()
        output =  await super().get(*args, **kwargs)
        #print(output)
        print(int(dict(output.raw_headers)[b'X-RateLimit-Remaining']))
        return output

    async def post(self, *args, **kwargs):
        await self.rate_limiter.rate_limit()
        output =  await super().post(*args, **kwargs)
        #print(output)
        print(int(dict(output.raw_headers)[b'X-RateLimit-Remaining']))
        return output
    """
    async def get(self, *args, **kwargs):
            loop = get_running_loop()
            await self.rate_limiter.rate_limit()
            uuid_it = uuid.uuid4()
            print(f"start: {loop.time()} - {uuid_it}")
            output = await super().get(*args, **kwargs)
            print(f"end: {loop.time()} - {uuid_it}")
            print(int(dict(output.raw_headers)[b'X-RateLimit-Remaining']))
            #print(output)
            return output

    async def post(self, *args, **kwargs):
            loop = get_running_loop()
            await self.rate_limiter.rate_limit()
            uuid_it = uuid.uuid4()
            print(f"start: {loop.time()} - {uuid_it}")
            output = await super().post(*args, **kwargs)
            print(f"end: {loop.time()} - {uuid_it}")
            print(int(dict(output.raw_headers)[b'X-RateLimit-Remaining']))
            #print(output)
            return output


    

@dataclass
class BaseNativeQuery(Generic[NativeData], AbstractNativeQuery):
    coroutine_function: Callable[[NewAsyncClient], Awaitable[NativeData]]
    metadata: Dict[str, str]
    def count_api_calls(self):
        return sum(self.metadata.values())
    def count_api_calls_by_method(self, method: str):
        return self.metadata[method]

Query = TypeVar('Query')
Data = TypeVar('Data')


class BaseBackendQueryEngine(
    Generic[Query, Data, NativeData], 
    SlightlyLessAbstractQueryEngine[Query, Data, BaseNativeQuery[NativeData], NativeData]
):
    async def _query_to_awaitable(self, query: Query) -> Tuple[coroutine, Dict[str, str]]:
        raise NotImplementedError('This method is required for query_to_native')
    async def _query_to_native(self, query: Query) -> BaseNativeQuery[NativeData]:
        awaitable, metadata = await _query_to_awaitable(query)
        return BaseNativeQuery(awaitable, metadata)

    async def _run_native_query(self, query: BaseNativeQuery[NativeData]) -> NativeData:
        print('here')
        async with NewAsyncClient() as client:
            results = await query.awaitable(client)
        return results
    
    async def _post_process(self, query: BaseNativeQuery[NativeData], data):
        return data


    #Put post process as no op


class BasePaperSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[PaperSearchQuery, PaperData, NativeData]
):
    pass


class BaseAuthorSearchQueryEngine(
    Generic[NativeData], 
    BaseBackendQueryEngine[AuthorSearchQuery, AuthorData, NativeData]
):
    pass
