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
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from testing_support.asgi_testing import AsgiTest
from newrelic.api.transaction import current_transaction


class HandledError(Exception):
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


async def error_handler(request, exc):
    return PlainTextResponse("Dude, your app crashed", status_code=500)


routes = [
    Route("/index", index),
    Route("/non_async", non_async),
    Route("/runtime_error", runtime_error),
    Route("/handled_error", handled_error),
]

app = Starlette(routes=routes)
app.add_exception_handler(Exception, error_handler)
app.add_exception_handler(HandledError, error_handler)

target_application = AsgiTest(app)
