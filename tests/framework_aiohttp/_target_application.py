import asyncio
from aiohttp import web


@asyncio.coroutine
def index(request):
    yield
    return web.Response(text='Hello Aiohttp!')


@asyncio.coroutine
def error(request):
    raise ValueError("I'm bad at programming...")


class HelloWorldView(web.View):

    @asyncio.coroutine
    def _respond(self):
        yield
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
    app.router.add_route('*', '/error', error)
    return app
