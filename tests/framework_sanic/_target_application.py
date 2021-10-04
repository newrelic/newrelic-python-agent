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

from sanic import Blueprint, Sanic
from sanic.exceptions import NotFound, SanicException, ServerError
from sanic.handlers import ErrorHandler
from sanic.response import json, stream
from sanic.router import Router
from sanic.views import HTTPMethodView


class MethodView(HTTPMethodView):
    async def get(self, request):
        return json({"hello": "world"})

    post = get
    put = get
    patch = get
    delete = get


class CustomErrorHandler(ErrorHandler):
    def response(self, request, exception):
        if isinstance(exception, ZeroDivisionError):
            raise ValueError("Value Error")
        else:
            base_response = ErrorHandler.response
            if hasattr(base_response, "__wrapped__"):
                base_response = base_response.__wrapped__

            return base_response(self, request, exception)

    def add(self, exception, handler, *args, **kwargs):
        base_add = ErrorHandler.add
        if hasattr(base_add, "__wrapped__"):
            base_add = base_add.__wrapped__
        base_add(self, exception, handler)


class CustomRouter(Router):
    def __init__(self):
        try:
            super().__init__(app=None)
        except TypeError:
            super().__init__()

    def add(self, *args, **kwargs):
        base_add = Router.add
        if hasattr(base_add, "__wrapped__"):
            base_add = base_add.__wrapped__
        return base_add.__get__(self, Router)(*args, **kwargs)

    def get(self, *args):
        base_get = Router.get
        if hasattr(base_get, "__wrapped__"):
            base_get = base_get.__wrapped__

        if len(args) == 1:
            path = args[0].path
        else:
            path = args[0]

        bound_get = base_get.__get__(self, Router)
        get_results = list(bound_get(*args))
        if path == "/server-error":
            from sanic.exceptions import ServerError

            raise ServerError("Server Error")
        return get_results


try:
    error_handler = CustomErrorHandler(fallback="text")
except TypeError:
    error_handler = CustomErrorHandler()

router = CustomRouter()
app = Sanic(name="test app", error_handler=error_handler, router=router)
router.app = app
blueprint = Blueprint("test_bp")


@app.route("/")
async def index(request):
    return json({"hello": "world"})


@app.route("/error")
async def error(request):
    raise ValueError("Exception")


# see write_callback in confest.create_request_coroutine
@app.route("/write_response_error")
async def write_response_error(request):
    return json({"url": "write_response_error"})


@app.route("/404")
async def not_found(request):
    raise NotFound("Not found")


@app.route("/zero")
async def zero_division_error(request):
    1 / 0


@app.middleware("request")
async def request_middleware(request):
    return None


@blueprint.middleware("request")
async def blueprint_middleware(request):
    return None


# register the middleware a second time, testing that the `request_middleware`
# function is not getting double wrapped
app.register_middleware(request_middleware)


@app.route("/streaming")
async def streaming(request):
    async def streaming_fn(response):
        response.write("foo")
        response.write("bar")

    return stream(streaming_fn)


# Fake websocket endpoint to enable websockets on the server
@app.websocket("/socket")
async def socket(request, ws):
    assert False


@app.route("/custom-header/<header_key>/<header_value>")
async def custom_header(request, header_key, header_value):
    custom_headers = {header_key: header_value}
    return json({"hello": "world"}, headers=custom_headers)


@app.route("/server-error")
async def server_error(request):
    raise AssertionError("This handler should never be reached!")


class CustomExceptionSync(SanicException):
    pass


class CustomExceptionAsync(SanicException):
    pass


@app.exception(ServerError)
def handle_server_error(request, exception):
    pass


@app.exception(CustomExceptionSync)
def handle_custom_exception_sync(request, exception):
    raise SanicException("something went wrong")


@app.exception(CustomExceptionAsync)
async def handle_custom_exception_async(request, exception):
    raise SanicException("something went wrong")


@app.route("/sync-error")
async def sync_error(request):
    raise CustomExceptionSync("something went wrong")


@app.route("/async-error")
async def async_error(request):
    raise CustomExceptionAsync("something went wrong")


@blueprint.route("/blueprint")
async def blueprint_route(request):
    async def streaming_fn(response):
        response.write("foo")

    return stream(streaming_fn)


app.blueprint(blueprint)
app.add_route(MethodView.as_view(), "/method_view")

if not getattr(router, "finalized", True):
    router.finalize()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
