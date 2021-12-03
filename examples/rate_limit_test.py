from matchmaker.query_engine.backends.web import NewAsyncClient
import asyncio

import time
async def main():
    async with NewAsyncClient() as client:
        request = []
        for i in range(9):
            async def evaluate_url(url):
                result = await client.get(url)
                return result
                
            result = evaluate_url('https://dreamingspires.dev/')
            request.append(result)
        await asyncio.gather(*request)


asyncio.run(main())