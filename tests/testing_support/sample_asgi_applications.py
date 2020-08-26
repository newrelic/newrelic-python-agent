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

from newrelic.api.asgi_application import ASGIApplicationWrapper


class simple_app_v2_raw:
    def __init__(self, scope):
        assert scope["type"] == "http"

    async def __call__(self, receive, send):
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body"})


async def simple_app_v3_raw(scope, receive, send):
    if scope["type"] != "http":
        raise ValueError("unsupported")

    await send({"type": "http.response.start", "status": 200})
    await send({"type": "http.response.body"})


class AppWithDescriptor:
    @ASGIApplicationWrapper
    async def method(self, scope, receive, send):
        return await simple_app_v3_raw(scope, receive, send)

    @ASGIApplicationWrapper
    @classmethod
    async def cls(cls, scope, receive, send):
        return await simple_app_v3_raw(scope, receive, send)

    @ASGIApplicationWrapper
    @staticmethod
    async def static(scope, receive, send):
        return await simple_app_v3_raw(scope, receive, send)


simple_app_v2 = ASGIApplicationWrapper(simple_app_v2_raw)
simple_app_v3 = ASGIApplicationWrapper(simple_app_v3_raw)
