import asyncio
from aiohttp.test_utils import TestServer as _TestServer


class AwaitHandlerServer(_TestServer):
    @asyncio.coroutine
    def _make_factory(self, **kwargs):
        server = yield from super(AwaitHandlerServer, self)._make_factory(
                **kwargs)

        handler = server.request_handler

        async def coro_awaits(request):
            return await handler(request)

        server.request_handler = coro_awaits
        return server
