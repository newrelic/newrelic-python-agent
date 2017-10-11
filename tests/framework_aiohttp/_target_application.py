import asyncio
from aiohttp import web


@asyncio.coroutine
def index(request):
    yield
    return web.Response(text='Hello Aiohttp!')


@asyncio.coroutine
def error(request):
    raise ValueError("I'm bad at programming...")


@asyncio.coroutine
def non_500_error(request):
    raise web.HTTPGone()


@asyncio.coroutine
def raise_404(request):
    raise web.HTTPNotFound()


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


class KnownException(Exception):
    pass


class KnownErrorView(web.View):

    @asyncio.coroutine
    def _respond(self):
        try:
            yield
        except KnownException:
            pass
        finally:
            return web.Response(text='Hello Aiohttp!')

    get = _respond
    post = _respond
    put = _respond
    patch = _respond
    delete = _respond


def make_app(middlewares=None, loop=None):
    app = web.Application(middlewares=middlewares, loop=loop)
    app.router.add_route('*', '/coro', index)
    app.router.add_route('*', '/class', HelloWorldView)
    app.router.add_route('*', '/error', error)
    app.router.add_route('*', '/known_error', KnownErrorView)
    app.router.add_route('*', '/non_500_error', non_500_error)
    app.router.add_route('*', '/raise_404', raise_404)

    return app
