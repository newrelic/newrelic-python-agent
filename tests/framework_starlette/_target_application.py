# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from starlette.applications import Starlette
from starlette.background import BackgroundTasks
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from testing_support.asgi_testing import AsgiTest
from newrelic.api.transaction import current_transaction

try:
    from starlette.middleware import Middleware
except ImportError:
    Middleware = None


class HandledError(Exception):
    pass


class NonAsyncHandledError(Exception):
    pass


class CoolStuffError(Exception):
    pass


async def index(request):
    return PlainTextResponse("Hello, world!")


def non_async(request):
    assert current_transaction()
    return PlainTextResponse("Not async!")


async def runtime_error(request):
    raise RuntimeError("Oopsies...")


async def handled_error(request):
    raise HandledError("it's cool")


def non_async_handled_error(request):
    raise NonAsyncHandledError("No problems here!")


async def async_error_handler(request, exc):
    return PlainTextResponse("Dude, your app crashed - async style", status_code=500)


def non_async_error_handler(request, exc):
    return PlainTextResponse("Dude, your app crashed", status_code=500)


async def its_cool(request, exc):
    return PlainTextResponse("It's cool yo!", status_code=200)


async def non_error_but_error(request):
    raise CoolStuffError("okeedokee")


async def run_bg_task(request):
    tasks = BackgroundTasks()
    tasks.add_task(bg_task_async)
    tasks.add_task(bg_task_non_async)
    return PlainTextResponse("Hello, world!", background=tasks)


async def bg_task_async():
    pass


def bg_task_non_async():
    pass

routes = [
    Route("/index", index),
    Route("/non_async", non_async),
    Route("/runtime_error", runtime_error),
    Route("/handled_error", handled_error),
    Route("/non_async_handled_error", non_async_handled_error),
    Route("/non_error_but_error", non_error_but_error),
    Route("/run_bg_task", run_bg_task),
]


def middleware(app):
    async def middleware(scope, receive, send):
        return await app(scope, receive, send)

    return middleware


if Middleware:
    app = Starlette(routes=routes, middleware=[Middleware(middleware)])
else:
    app = Starlette(routes=routes)
    app.add_middleware(middleware)
# app.add_exception_handler(Exception, async_error_handler)
app.add_exception_handler(HandledError, async_error_handler)
app.add_exception_handler(NonAsyncHandledError, non_async_error_handler)
app.add_exception_handler(CoolStuffError, its_cool)
app.add_middleware(middleware)


@app.middleware("http")
async def middleware_decorator(request, call_next):
    return await call_next(request)

target_application = AsgiTest(app)
