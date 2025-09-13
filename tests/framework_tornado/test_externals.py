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

import io
import sys

import pytest
from testing_support.fixtures import override_application_settings
from testing_support.mock_external_http_server import MockExternalHTTPHResponseHeadersServer
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace

is_pypy = hasattr(sys, "pypy_version_info")


@pytest.fixture(scope="module")
def external():
    external = MockExternalHTTPHResponseHeadersServer()
    with external:
        yield external


@background_task(name="make_request")
def make_request(port, req_type, client_cls, count=1, raise_error=True, as_kwargs=True, **kwargs):
    import tornado.concurrent
    import tornado.gen
    import tornado.httpclient
    import tornado.ioloop

    class CustomAsyncHTTPClient(tornado.httpclient.AsyncHTTPClient):
        def fetch_impl(self, request, callback):
            out = []
            for k, v in request.headers.items():
                out.append(f"{k}: {v}")
            body = "\n".join(out).encode("utf-8")
            response = tornado.httpclient.HTTPResponse(request=request, code=200, buffer=io.BytesIO(body))
            callback(response)

    cls = tornado.httpclient.AsyncHTTPClient
    if client_cls == "AsyncHTTPClient":
        cls.configure(None)
    elif client_cls == "CurlAsyncHTTPClient":
        if is_pypy:
            pytest.skip("Pypy not supported by Pycurl")
        import tornado.curl_httpclient

        cls.configure(tornado.curl_httpclient.CurlAsyncHTTPClient)
    elif client_cls == "HTTPClient":
        cls = tornado.httpclient.HTTPClient
    elif client_cls == "CustomAsyncHTTPClient":
        cls.configure(CustomAsyncHTTPClient)
    else:
        raise ValueError(f"Received unknown client type: {client_cls}")

    client = cls(force_instance=True)
    callback = None

    uri = f"http://localhost:{port}"
    if req_type == "class":
        req = tornado.httpclient.HTTPRequest(uri, **kwargs)
        kwargs = {}
    elif req_type == "uri":
        req = uri
    else:
        raise ValueError(f"Received unknown request type: {req_type}")

    @tornado.gen.coroutine
    def _make_request():
        if as_kwargs:
            futures = [client.fetch(req, raise_error=raise_error, **kwargs) for _ in range(count)]
        elif tornado.version_info < (6, 0):
            futures = [client.fetch(req, callback, raise_error, **kwargs) for _ in range(count)]
        else:
            futures = [client.fetch(req, raise_error, **kwargs) for _ in range(count)]

        assert all(isinstance(f, tornado.concurrent.Future) for f in futures)

        if count > 1:
            responses = yield tornado.gen.multi_future(futures)
            response = responses[0]
        else:
            response = yield futures[0]

        raise tornado.gen.Return(response)

    if client_cls == "HTTPClient":
        for _ in range(count):
            response = client.fetch(req, raise_error=raise_error, **kwargs)
        return response
    else:
        response = tornado.ioloop.IOLoop.current().run_sync(_make_request)
        return response


@pytest.mark.parametrize(
    "client_class,as_kwargs",
    [
        ("AsyncHTTPClient", True),
        ("AsyncHTTPClient", False),
        ("CurlAsyncHTTPClient", True),
        ("CurlAsyncHTTPClient", False),
        ("CustomAsyncHTTPClient", True),
        ("CustomAsyncHTTPClient", False),
        ("HTTPClient", True),
    ],
)
@pytest.mark.parametrize("span_events", [True, False])
@pytest.mark.parametrize("request_type", ["uri", "class"])
@pytest.mark.parametrize("num_requests", [1, 2])
def test_httpclient(request_type, client_class, num_requests, span_events, external, as_kwargs):
    port = external.port

    expected_metrics = [(f"External/localhost:{port}/tornado/GET", num_requests)]

    @override_application_settings({"distributed_tracing.enabled": True, "span_events.enabled": span_events})
    @validate_transaction_metrics(
        "test_externals:test_httpclient",
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics,
    )
    @background_task(name="test_externals:test_httpclient")
    def _test():
        headers = {}

        response = make_request(
            port, request_type, client_class, headers=headers, count=num_requests, as_kwargs=as_kwargs
        )
        assert response.code == 200

        body = response.body
        if hasattr(body, "decode"):
            body = body.decode("utf-8")

        headers = {}
        for header_line in body.split("\n"):
            if ":" not in header_line:
                continue
            header_key, header_val = header_line.split(":", 1)
            header_key = header_key.strip()
            header_val = header_val.strip()
            headers[header_key] = header_val

    _test()


@pytest.mark.parametrize("client_class", ["AsyncHTTPClient", "CurlAsyncHTTPClient", "HTTPClient"])
@validate_transaction_metrics("make_request", background_task=True)
def test_httpclient_invalid_method(client_class, external):
    with pytest.raises(KeyError):
        make_request(external.port, "uri", client_class, method="COOKIES")


@pytest.mark.parametrize("client_class", ["AsyncHTTPClient", "CurlAsyncHTTPClient", "HTTPClient"])
@validate_transaction_metrics("make_request", background_task=True)
def test_httpclient_invalid_kwarg(client_class, external):
    with pytest.raises(TypeError):
        make_request(external.port, "uri", client_class, boop="1234")


def test_httpclient_fetch_crashes(external):
    @validate_transaction_metrics(
        "test_httpclient_fetch_crashes",
        background_task=True,
        rollup_metrics=[(f"External/localhost:{external.port}/tornado/GET", 1)],
        scoped_metrics=[(f"External/localhost:{external.port}/tornado/GET", 1)],
    )
    @background_task(name="test_httpclient_fetch_crashes")
    def _test():
        import tornado.httpclient

        class CrashClient(tornado.httpclient.AsyncHTTPClient):
            def fetch_impl(self, *args, **kwargs):
                raise ValueError("BOOM")

        client = CrashClient(force_instance=True)

        port = external.port
        with pytest.raises(ValueError):
            tornado.ioloop.IOLoop.current().run_sync(lambda: client.fetch(f"http://localhost:{port}"))

    _test()


def test_httpclient_fetch_inside_terminal_node(external):
    @validate_transaction_metrics(
        "test_httpclient_fetch_inside_terminal_node",
        background_task=True,
        rollup_metrics=[(f"External/localhost:{external.port}/tornado/GET", None)],
        scoped_metrics=[(f"External/localhost:{external.port}/tornado/GET", None)],
    )
    @background_task(name="test_httpclient_fetch_inside_terminal_node")
    def _test():
        # Test that our instrumentation correctly handles the case when the parent
        # is a terminal node
        import tornado.gen
        import tornado.httpclient
        import tornado.ioloop

        client = tornado.httpclient.AsyncHTTPClient(force_instance=True)

        # This is protecting against a "pop_current" when the external trace never
        # actually gets pushed
        port = external.port

        @tornado.gen.coroutine
        def _make_request():
            with FunctionTrace(name="parent", terminal=True):
                response = yield client.fetch(f"http://localhost:{port}")
            return response

        response = tornado.ioloop.IOLoop.current().run_sync(_make_request)
        assert response.code == 200

    _test()
