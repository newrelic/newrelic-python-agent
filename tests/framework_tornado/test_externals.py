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
import socket
import sys

import pytest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.mock_external_http_server import (
    MockExternalHTTPHResponseHeadersServer,
    MockExternalHTTPServer,
)
from testing_support.validators.validate_distributed_tracing_header import (
    validate_distributed_tracing_header,
)
from testing_support.validators.validate_outbound_headers import (
    validate_outbound_headers,
)

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction

ENCODING_KEY = "1234567890123456789012345678901234567890"

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
                out.append("%s: %s" % (k, v))
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
        raise ValueError("Received unknown client type: %s" % client_cls)

    client = cls(force_instance=True)
    callback = None

    uri = "http://localhost:%s" % port
    if req_type == "class":
        req = tornado.httpclient.HTTPRequest(uri, **kwargs)
        kwargs = {}
    elif req_type == "uri":
        req = uri
    else:
        raise ValueError("Received unknown request type: %s" % req_type)

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
@pytest.mark.parametrize(
    "cat_enabled,user_header,span_events,distributed_tracing",
    [
        (True, None, False, False),
        (True, "X-NewRelic-ID", False, False),
        (True, "X-NewRelic-Transaction", False, False),
        (False, None, True, True),
        (False, None, False, True),
    ],
)
# @pytest.mark.parametrize('cat_enabled,user_header', [
#    (True, None),
#    (True, 'X-NewRelic-ID'),
#    (True, 'X-NewRelic-Transaction'),
#    (False, None),
# ])
@pytest.mark.parametrize("request_type", ["uri", "class"])
@pytest.mark.parametrize("num_requests", [1, 2])
def test_httpclient(
    cat_enabled,
    request_type,
    client_class,
    user_header,
    num_requests,
    distributed_tracing,
    span_events,
    external,
    as_kwargs,
):

    port = external.port

    expected_metrics = [("External/localhost:%s/tornado/GET" % port, num_requests)]

    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
            "cross_application_tracer.enabled": not distributed_tracing,
        }
    )
    @validate_transaction_metrics(
        "test_externals:test_httpclient",
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics,
    )
    @background_task(name="test_externals:test_httpclient")
    def _test():
        headers = {}
        if user_header:
            headers = {user_header: "USER"}

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

        # User headers override all inserted NR headers
        if user_header:
            assert headers[user_header] == "USER"
        elif cat_enabled:
            t = current_transaction()
            assert t
            t._test_request_headers = headers

            if distributed_tracing:
                validate_distributed_tracing_header(header="Newrelic")
            else:
                validate_outbound_headers()
        else:
            # new relic shouldn't add anything to the outgoing
            assert "x-newrelic" not in body, body

        assert "X-NewRelic-App-Data" not in headers

    _test()


CAT_RESPONSE_CODE = None


def cat_response_handler(self):
    global CAT_RESPONSE_CODE
    # payload
    # (
    #     u'1#1', u'WebTransaction/Function/app:beep',
    #     0, 1.23, -1,
    #     'dd4a810b7cb7f937',
    #     False,
    # )
    cat_response_header = (
        "X-NewRelic-App-Data",
        "ahACFwQUGxpuVVNmQVVbRVZbTVleXBxyQFhUTFBfXx1SREUMVV1cQBMeAxgEGAULFR0AHhFQUQJWAAgAUwVQVgJQDgsOEh1UUlhGU2o=",
    )
    self.send_response(CAT_RESPONSE_CODE)
    self.send_header(*cat_response_header)
    self.end_headers()
    self.wfile.write(b"Example Data")


@pytest.fixture(scope="module")
def cat_response_server():
    external = MockExternalHTTPServer(handler=cat_response_handler)
    with external:
        yield external


@pytest.mark.parametrize("client_class", ["AsyncHTTPClient", "CurlAsyncHTTPClient", "HTTPClient"])
@pytest.mark.parametrize("cat_enabled", [True, False])
@pytest.mark.parametrize("request_type", ["uri", "class"])
@pytest.mark.parametrize(
    "response_code,raise_error",
    [
        (500, True),
        (500, False),
        (200, False),
    ],
)
def test_client_cat_response_processing(
    cat_enabled, request_type, client_class, raise_error, response_code, cat_response_server
):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = response_code

    _custom_settings = {
        "cross_process_id": "1#1",
        "encoding_key": ENCODING_KEY,
        "trusted_account_ids": [1],
        "cross_application_tracer.enabled": cat_enabled,
        "distributed_tracing.enabled": not cat_enabled,
        "transaction_tracer.transaction_threshold": 0.0,
    }

    port = cat_response_server.port
    expected_metrics = [
        ("ExternalTransaction/localhost:%s/1#1/WebTransaction/Function/app:beep" % port, 1 if cat_enabled else None),
    ]

    @validate_transaction_metrics(
        "make_request", background_task=True, rollup_metrics=expected_metrics, scoped_metrics=expected_metrics
    )
    @override_application_settings(_custom_settings)
    def _test():
        import tornado
        import tornado.httpclient

        try:
            response = make_request(port, request_type, client_class, raise_error=raise_error)
        except tornado.httpclient.HTTPError as e:
            assert raise_error
            response = e.response
        else:
            assert not raise_error

        assert response.code == response_code

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
        rollup_metrics=[("External/localhost:%d/tornado/GET" % external.port, 1)],
        scoped_metrics=[("External/localhost:%d/tornado/GET" % external.port, 1)],
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
            tornado.ioloop.IOLoop.current().run_sync(lambda: client.fetch("http://localhost:%s" % port))

    _test()


def test_httpclient_fetch_inside_terminal_node(external):
    @validate_transaction_metrics(
        "test_httpclient_fetch_inside_terminal_node",
        background_task=True,
        rollup_metrics=[("External/localhost:%d/tornado/GET" % external.port, None)],
        scoped_metrics=[("External/localhost:%d/tornado/GET" % external.port, None)],
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
                response = yield client.fetch("http://localhost:%s" % port)
            return response

        response = tornado.ioloop.IOLoop.current().run_sync(_make_request)
        assert response.code == 200

    _test()
