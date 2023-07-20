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
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import (
    add_custom_attribute,
    current_transaction,
    ignore_transaction,
)


class simple_app_v2_raw:
    def __init__(self, scope):
        self.scope = scope

    async def __call__(self, receive, send):
        if self.scope["type"] == "lifespan":
            return await handle_lifespan(self.scope, receive, send)

        if self.scope["type"] != "http":
            raise ValueError("unsupported")

        if self.scope["path"] == "/exc":
            raise ValueError("whoopsies")
        elif self.scope["path"] == "/ignored":
            ignore_transaction()

        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body"})

        assert current_transaction() is None


class simple_app_v2_init_exc(simple_app_v2_raw):
    def __init__(self, scope):
        raise ValueError("oh no!")


async def simple_app_v3_raw(scope, receive, send):
    if scope["type"] == "lifespan":
        return await handle_lifespan(scope, receive, send)

    if scope["type"] != "http":
        raise ValueError("unsupported")

    if scope["path"] == "/exc":
        raise ValueError("whoopsies")
    elif scope["path"] == "/ignored":
        ignore_transaction()

    await send({"type": "http.response.start", "status": 200})
    await send({"type": "http.response.body"})

    assert current_transaction() is None


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


class AppWithCallRaw:
    async def __call__(self, scope, receive, send):
        return await simple_app_v3_raw(scope, receive, send)


class AppWithCall(AppWithCallRaw):
    @ASGIApplicationWrapper
    async def __call__(self, scope, receive, send):
        return await super(AppWithCall, self).__call__(scope, receive, send)


simple_app_v2 = ASGIApplicationWrapper(simple_app_v2_raw)
simple_app_v2_init_exc = ASGIApplicationWrapper(simple_app_v2_init_exc)
simple_app_v3 = ASGIApplicationWrapper(simple_app_v3_raw)


@ASGIApplicationWrapper
async def normal_asgi_application(scope, receive, send):
    output = b"<html><head>header</head><body><p>RESPONSE</p></body></html>"
    add_custom_attribute("puppies", "test_value")
    add_custom_attribute("sunshine", "test_value")

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    try:
        raise ValueError("Transaction had bad value")
    except ValueError:
        notice_error(attributes={"ohnoes": "param-value"})

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


async def handle_lifespan(scope, receive, send):
    """Handle lifespan protocol with no-ops to allow more compatibility."""
    while True:
        txn = current_transaction()
        if txn:
            txn.ignore_transaction = True

        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return
