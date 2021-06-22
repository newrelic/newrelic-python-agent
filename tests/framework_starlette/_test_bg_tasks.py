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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from testing_support.asgi_testing import AsgiTest


class ASGIStyleMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        response = await self.app(scope, receive, send)
        return response


class BaseHTTPStyleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # simple middleware that does absolutely nothing
        response = await call_next(request)
        return response


async def run_async_bg_task(request):
    tasks = BackgroundTasks()
    tasks.add_task(async_bg_task)
    return PlainTextResponse("Hello, world!", background=tasks)


async def run_sync_bg_task(request):
    tasks = BackgroundTasks()
    tasks.add_task(sync_bg_task)
    return PlainTextResponse("Hello, world!", background=tasks)


async def async_bg_task():
    pass


async def sync_bg_task():
    pass


routes = [
    Route("/async", run_async_bg_task),
    Route("/sync", run_sync_bg_task),
]

# Generating target applications
target_application = {}

app = Starlette(routes=routes)
app.add_middleware(ASGIStyleMiddleware)
target_application["asgi"] = AsgiTest(app)

app = Starlette(routes=routes)
app.add_middleware(BaseHTTPStyleMiddleware)
target_application["basehttp"] = AsgiTest(app)

app = Starlette(routes=routes)
target_application["none"] = AsgiTest(app)
