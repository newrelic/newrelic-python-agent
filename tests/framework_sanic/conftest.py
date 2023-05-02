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

import asyncio

import pytest

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture  # noqa: F401; pylint: disable=W0611

from newrelic.common.object_wrapper import (  # noqa: F401 pylint: disable=W0611
    transient_function_wrapper,
)


_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_sanic)", default_settings=_default_settings
)


RESPONSES = []

loop = None


def create_request_class(app, method, url, headers=None, loop=None):
    from sanic.request import Request

    try:
        _request = Request(
            method=method.upper(),
            url_bytes=url.encode("utf-8"),
            headers=headers,
            version="1.0",
            transport=None,
        )
    except TypeError:
        _request = Request(
            app=app,
            method=method.upper(),
            url_bytes=url.encode("utf-8"),
            headers=headers,
            version="1.0",
            transport=None,
        )

    try:
        # Manually initialize HTTP protocol
        from sanic.http import Http, Stage
        from sanic.server import HttpProtocol

        class MockProtocol(HttpProtocol):
            async def send(*args, **kwargs):  # pylint: disable=E0211
                return

        proto = MockProtocol(loop=loop, app=app)
        proto.recv_buffer = bytearray()
        http = Http(proto)

        if hasattr(http, "init_for_request"):
            http.init_for_request()

        http.stage = Stage.HANDLER
        http.response_func = http.http1_response_header
        _request.stream = http
    except ImportError:
        pass

    return _request


def create_request_coroutine(app, method, url, headers=None, loop=None):
    headers = headers or {}
    try:
        coro = app.handle_request(create_request_class(app, method, url, headers, loop=loop))
    except TypeError:

        def write_callback(response):
            response.raw_headers = response.output()
            if b"write_response_error" in response.raw_headers:
                raise ValueError("write_response_error")

            if response not in RESPONSES:
                RESPONSES.append(response)

        async def stream_callback(response):
            response.raw_headers = response.get_headers()
            if response not in RESPONSES:
                RESPONSES.append(response)

        coro = app.handle_request(
            create_request_class(app, method, url, headers, loop=loop),
            write_callback,
            stream_callback,
        )

    return coro


def request(app, method, url, headers=None):
    global loop
    if loop is None:
        loop = asyncio.new_event_loop()

    if not getattr(app.router, "finalized", True):
        # Handle startup if the router hasn't been finalized.
        # Older versions don't have this requirement or variable so
        # the default should be True.
        if hasattr(app, "_startup"):
            loop.run_until_complete(app._startup())
        else:
            app.router.finalize()
    # Starting in 22.9.0 sanic introduced an API to control middleware ordering.
    # This included a new method called finalize_middleware that sets the middleware
    # to be used on the request.route during the app._startup. In order to register
    # new middleware the finalize_middleware must be called.
    elif hasattr(app, "finalize_middleware"):
        app.finalize_middleware()

    coro = create_request_coroutine(app, method, url, headers, loop)
    loop.run_until_complete(coro)
    return RESPONSES.pop()


class TestApplication(object):
    def __init__(self, app):
        self.app = app

    def fetch(self, method, url, headers=None):
        return request(self.app, method, url, headers)


@pytest.fixture()
def app():
    from _target_application import app

    return TestApplication(app)


@pytest.fixture(autouse=True)
def capture_requests(monkeypatch):
    from sanic.response import BaseHTTPResponse

    original = BaseHTTPResponse.__init__

    def capture(*args, **kwargs):
        original(*args, **kwargs)
        response = args[0]
        if getattr(response, "status", None) is None:
            response.status = 200

        if response not in RESPONSES:
            RESPONSES.append(response)

    monkeypatch.setattr(BaseHTTPResponse, "__init__", capture)
