from aiohttp import web


async def handler(request):
    return web.Response(text='PONG')


async def app_factory():
    app = web.Application()
    app.router.add_get('/', handler)
    return app
