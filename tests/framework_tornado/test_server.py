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

import pytest
from testing_support.fixtures import (
    function_not_called,
    override_application_settings,
    override_generic_settings,
    override_ignore_status_codes,
)
from testing_support.validators.validate_code_level_metrics import (
    validate_code_level_metrics,
)
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_event_attributes import (
    validate_transaction_event_attributes,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.core.config import global_settings


@pytest.mark.parametrize(
    "uri,name,metrics, method_metric",
    (
        # ('/native-simple', '_target_application:NativeSimpleHandler.get', None,
        #         True),
        # ('/simple', '_target_application:SimpleHandler.get', None, True),
        ("/call-simple", "_target_application:CallSimpleHandler.get", None, True),
        ("/super-simple", "_target_application:SuperSimpleHandler.get", None, True),
        ("/coro", "_target_application:CoroHandler.get", None, False),
        ("/fake-coro", "_target_application:FakeCoroHandler.get", None, False),
        ("/coro-throw", "_target_application:CoroThrowHandler.get", None, False),
        ("/init", "_target_application:InitializeHandler.get", None, True),
        ("/multi-trace", "_target_application:MultiTraceHandler.get", [("Function/trace", 2)], True),
    ),
)
@override_application_settings({"attributes.include": ["request.*"]})
def test_server(app, uri, name, metrics, method_metric):
    FRAMEWORK_METRIC = "Python/Framework/Tornado/%s" % app.tornado_version
    METHOD_METRIC = "Function/%s" % name

    metrics = metrics or []
    metrics.append((FRAMEWORK_METRIC, 1))
    metrics.append((METHOD_METRIC, 1 if method_metric else None))

    host = "127.0.0.1:" + str(app.get_http_port())
    namespace, func_name = name.split(".")
    namespace = namespace.replace(":", ".")

    @validate_transaction_metrics(
        name,
        rollup_metrics=metrics,
    )
    @validate_transaction_event_attributes(
        required_params={"agent": ("response.headers.contentType",), "user": (), "intrinsic": ()},
        exact_attrs={
            "agent": {
                "request.headers.contentType": "1234",
                "request.headers.host": host,
                "request.method": "GET",
                "request.uri": uri,
                "response.status": "200",
            },
            "user": {},
            "intrinsic": {"port": app.get_http_port()},
        },
    )
    def _test():
        response = app.fetch(uri, headers=(("Content-Type", "1234"),))
        assert response.code == 200

    if method_metric:
        _test = validate_code_level_metrics(namespace, func_name)(_test)

    _test()


@pytest.mark.parametrize(
    "uri,name,metrics,method_metric",
    (
        ("/native-simple", "_target_application:NativeSimpleHandler.get", None, True),
        ("/simple", "_target_application:SimpleHandler.get", None, True),
        ("/call-simple", "_target_application:CallSimpleHandler.get", None, True),
        ("/super-simple", "_target_application:SuperSimpleHandler.get", None, True),
        ("/coro", "_target_application:CoroHandler.get", None, False),
        ("/fake-coro", "_target_application:FakeCoroHandler.get", None, False),
        ("/coro-throw", "_target_application:CoroThrowHandler.get", None, False),
        ("/init", "_target_application:InitializeHandler.get", None, True),
        ("/ensure-future", "_target_application:EnsureFutureHandler.get", [("Function/trace", None)], True),
        ("/multi-trace", "_target_application:MultiTraceHandler.get", [("Function/trace", 2)], True),
    ),
)
def test_concurrent_inbound_requests(app, uri, name, metrics, method_metric):
    from tornado import gen

    FRAMEWORK_METRIC = "Python/Framework/Tornado/%s" % app.tornado_version
    METHOD_METRIC = "Function/%s" % name

    metrics = metrics or []
    metrics.append((FRAMEWORK_METRIC, 1))
    metrics.append((METHOD_METRIC, 1 if method_metric else None))

    namespace, func_name = name.split(".")
    namespace = namespace.replace(":", ".")

    @validate_transaction_count(2)
    @validate_transaction_metrics(
        name,
        rollup_metrics=metrics,
    )
    def _test():
        url = app.get_url(uri)
        coros = (app.http_client.fetch(url) for _ in range(2))
        responses = app.io_loop.run_sync(lambda: gen.multi(coros))

        for response in responses:
            assert response.code == 200

    if method_metric:
        _test = validate_code_level_metrics(namespace, func_name)(_test)

    _test()


@validate_code_level_metrics("_target_application.CrashHandler", "get")
@validate_transaction_metrics("_target_application:CrashHandler.get")
@validate_transaction_errors(["builtins:ValueError"])
def test_exceptions_are_recorded(app):
    response = app.fetch("/crash")
    assert response.code == 500


@pytest.mark.parametrize(
    "nr_enabled,ignore_status_codes",
    [
        (True, [405]),
        (True, []),
        (False, None),
    ],
)
def test_unsupported_method(app, nr_enabled, ignore_status_codes):
    def _test():
        response = app.fetch("/simple", method="TEAPOT", body=b"", allow_nonstandard_methods=True)
        assert response.code == 405

    if nr_enabled:
        _test = override_ignore_status_codes(ignore_status_codes)(_test)
        _test = validate_transaction_metrics("_target_application:SimpleHandler")(_test)

        if ignore_status_codes:
            _test = validate_transaction_errors(errors=[])(_test)
        else:
            _test = validate_transaction_errors(errors=["tornado.web:HTTPError"])(_test)
    else:
        settings = global_settings()
        _test = override_generic_settings(settings, {"enabled": False})(_test)

    _test()


@validate_transaction_errors(errors=[])
@validate_transaction_metrics("tornado.web:ErrorHandler")
@validate_transaction_event_attributes(
    required_params={"agent": (), "user": (), "intrinsic": ()},
    exact_attrs={
        "agent": {"request.uri": "/does-not-exist"},
        "user": {},
        "intrinsic": {},
    },
)
def test_not_found(app):
    response = app.fetch("/does-not-exist")
    assert response.code == 404


@override_generic_settings(
    global_settings(),
    {
        "enabled": False,
    },
)
@function_not_called("newrelic.core.stats_engine", "StatsEngine.record_transaction")
def test_nr_disabled(app):
    response = app.fetch("/simple")
    assert response.code == 200


@pytest.mark.parametrize(
    "uri,name",
    (
        ("/web-socket", "_target_application:WebSocketHandler"),
        ("/call-web-socket", "_target_application:WebNestedHandler"),
    ),
)
def test_web_socket(uri, name, app):
    # import asyncio

    from tornado.websocket import websocket_connect

    namespace, func_name = name.split(":")

    @validate_transaction_metrics(
        name,
        rollup_metrics=[("Function/%s" % name, None)],
    )
    @validate_code_level_metrics(namespace, func_name)
    def _test():
        url = app.get_url(uri).replace("http", "ws")

        async def _connect():
            conn = await websocket_connect(url)
            return conn

        @validate_transaction_metrics(
            name,
        )
        def connect():
            return app.io_loop.run_sync(_connect)

        @function_not_called("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        def call(call):
            async def _call():
                await conn.write_message("test")
                resp = await conn.read_message()
                assert resp == "hello test"

            app.io_loop.run_sync(_call)

        conn = connect()
        call(conn)
        conn.close()

    _test()


LOOP_TIME_METRICS = (("EventLoop/Wait/" "WebTransaction/Function/_target_application:BlockingHandler.get", 1),)


@pytest.mark.parametrize("yield_before_finish", (True, False))
@validate_transaction_metrics(
    "_target_application:BlockingHandler.get",
    scoped_metrics=LOOP_TIME_METRICS,
)
def test_io_loop_blocking_time(app, yield_before_finish):
    from tornado import gen

    if yield_before_finish:
        url = app.get_url("/block-with-yield/2")
    else:
        url = app.get_url("/block/2")

    coros = (app.http_client.fetch(url) for _ in range(2))
    responses = app.io_loop.run_sync(lambda: gen.multi(coros))

    for response in responses:
        assert response.code == 200
