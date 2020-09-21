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
