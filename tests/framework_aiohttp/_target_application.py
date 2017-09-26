import asyncio
from aiohttp import web


@asyncio.coroutine
def index(request):
    return web.Response(text='Hello Aiohttp!')


class HelloWorldView(web.View):

    @asyncio.coroutine
    def _respond(self):
        return web.Response(text='Hello Aiohttp!')

    get = _respond
    post = _respond
    put = _respond
    patch = _respond
    delete = _respond


def make_app():
    app = web.Application()
    app.router.add_route('*', '/coro', index)
    app.router.add_route('*', '/class', HelloWorldView)
    return app
