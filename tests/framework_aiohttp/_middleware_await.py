from aiohttp import web


async def load_coro_awaits(app, handler):

    async def coro_awaits(request):
        try:
            return await handler(request)
        except Exception as e:
            return web.Response(status=500, text=str(e))

    return coro_awaits
