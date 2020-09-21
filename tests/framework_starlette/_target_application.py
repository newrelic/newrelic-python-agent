from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from testing_support.asgi_testing import AsgiTest


async def index(request):
    return PlainTextResponse('Hello, world!')

def non_async(request):
    return PlainTextResponse('Not async!')

async def error(request):
    raise RuntimeError('Oopsies...')

def startup():
    print('Ready to go')


routes = [
    Route('/index', index),
    Route('/non_async', non_async),
    Route('/error', error),

]

app = Starlette(debug=True, routes=routes, on_startup=[startup])

target_application = AsgiTest(app)
