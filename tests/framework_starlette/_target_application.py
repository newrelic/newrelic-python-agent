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
from starlette.exceptions import HTTPException
from testing_support.asgi_testing import AsgiTest
from newrelic.api.transaction import current_transaction
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name

try:
    from starlette.middleware import Middleware
except ImportError:
    Middleware = None


class HandledError(Exception):
    pass


class NonAsyncHandledError(Exception):
    pass


async def index(request):
    return PlainTextResponse("Hello, world!")


def non_async(request):
    assert current_transaction()
    return PlainTextResponse("Non async route")


async def runtime_error(request):
    raise RuntimeError("Runtime error")


async def handled_error(request):
    raise HandledError("Handled error")


def non_async_handled_error(request):
    raise NonAsyncHandledError("Non async handled error")


async def async_error_handler(request, exc):
    return PlainTextResponse("Async error handler", status_code=500)


def non_async_error_handler(request, exc):
    return PlainTextResponse("Non async error handler", status_code=500)


async def teapot(request):
    raise HTTPException(418, "I'm a teapot")


async def teapot_handler(request, exc):
    return PlainTextResponse("Teapot handler", status_code=418)


def missing_route_handler(request, exc):
    return PlainTextResponse("Missing route handler", status_code=404)


class CustomRoute(object):
    def __init__(self, route):
        self.route = route

    async def __call__(self, scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        with FunctionTrace(name=callable_name(self.route)):
            await self.route(None)


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
    Route("/418", teapot),
    Route("/non_async", non_async),
    Route("/runtime_error", runtime_error),
    Route("/handled_error", handled_error),
    Route("/non_async_handled_error", non_async_handled_error),
    Route("/raw_runtime_error", CustomRoute(runtime_error)),
    Route("/raw_http_error", CustomRoute(teapot)),
    Route("/run_bg_task", run_bg_task),
]


def middleware_factory(app):
    async def middleware(scope, receive, send):
        if scope["path"] == "/crash_me_now":
            raise ValueError("Value error")
        return await app(scope, receive, send)

    return middleware


async def middleware_decorator(request, call_next):
    return await call_next(request)


# Generating target applications
app_name_map = {
    "no_error_handler": (True, False, {}),
    "async_error_handler_no_middleware": (False, False, {Exception: async_error_handler}),
    "non_async_error_handler_no_middleware": (False, False, {}),
    "no_middleware": (False, False, {}),
    "debug_no_middleware": (False, True, {}),
    "teapot_exception_handler_no_middleware": (False, False, {}),
}


target_application = dict()
for app_name, flags in app_name_map.items():
    # Bind options
    middleware_on, debug, exception_handlers = flags

    # Instantiate app
    if not middleware_on:
        app = Starlette(debug=debug, routes=routes, exception_handlers=exception_handlers)
    else:
        if Middleware:
            app = Starlette(debug=debug, routes=routes, middleware=[Middleware(middleware_factory)], exception_handlers=exception_handlers)
        else:
            app = Starlette(debug=debug, routes=routes, exception_handlers=exception_handlers)
            # in earlier versions of starlette, middleware is not a legal argument on the Starlette application class
            # In order to keep the counts the same, we add the middleware twice using the add_middleware interface
            app.add_middleware(middleware_factory)

        app.add_middleware(middleware_factory)
        app.middleware("http")(middleware_decorator)

    # Adding custom exception handlers
    app.add_exception_handler(HandledError, async_error_handler)

    # Add exception handler multiple times to verify the handler is not double wrapped
    app.add_exception_handler(NonAsyncHandledError, non_async_error_handler)
    app.add_exception_handler(NonAsyncHandledError, non_async_error_handler)

    if app_name == "non_async_error_handler_no_middleware":
        app.add_exception_handler(Exception, non_async_error_handler)
        app.add_exception_handler(404, missing_route_handler)
    elif app_name == "teapot_exception_handler_no_middleware":
        app.add_exception_handler(418, teapot_handler)

    # Assign to dict
    target_application[app_name] = AsgiTest(app)
