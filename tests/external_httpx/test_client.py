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
from testing_support.fixtures import dt_enabled, override_application_settings, override_generic_settings
from testing_support.mock_external_http_server import MockExternalHTTPHResponseHeadersServer
from testing_support.validators.validate_cross_process_headers import validate_cross_process_headers
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_tt_segment_params import validate_tt_segment_params

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
from newrelic.core.config import global_settings

ENCODING_KEY = "1234567890123456789012345678901234567890"
SCOPED_METRICS = []
ROLLUP_METRICS = [("External/all", 2), ("External/allOther", 2)]

CAT_RESPONSE_CODE = None


def cat_response_handler(self):
    global CAT_RESPONSE_CODE
    if not CAT_RESPONSE_CODE:
        raise ValueError("CAT_RESPONSE_CODE must be a valid status_code.")

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


@pytest.fixture(scope="session")
def mock_server():
    external = MockExternalHTTPHResponseHeadersServer(handler=cat_response_handler)
    with external:
        yield external


@pytest.fixture()
def populate_metrics(mock_server, request):
    SCOPED_METRICS[:] = []
    method = request.getfixturevalue("method").upper()
    SCOPED_METRICS.append((f"External/localhost:{mock_server.port}/httpx/{method}", 2))


def exercise_sync_client(server, client, method, protocol="http"):
    with client as client:
        resolved_method = getattr(client, method)
        resolved_method(f"{protocol}://{server.host}:{server.port}")
        response = resolved_method(f"{protocol}://{server.host}:{server.port}")

    return response


@pytest.mark.parametrize("method", ("get", "options", "head", "post", "put", "patch", "delete"))
@validate_transaction_metrics(
    "test_sync_client", scoped_metrics=SCOPED_METRICS, rollup_metrics=ROLLUP_METRICS, background_task=True
)
@background_task(name="test_sync_client")
def test_sync_client(httpx, sync_client, mock_server, method):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    assert exercise_sync_client(mock_server, sync_client, method).status_code == 200


async def exercise_async_client(server, client, method, protocol="http"):
    async with client as client:
        resolved_method = getattr(client, method)
        responses = await asyncio.gather(
            resolved_method(f"{protocol}://{server.host}:{server.port}"),
            resolved_method(f"{protocol}://{server.host}:{server.port}"),
        )

    return responses


@pytest.mark.parametrize("method", ("get", "options", "head", "post", "put", "patch", "delete"))
@validate_transaction_metrics(
    "test_async_client", scoped_metrics=SCOPED_METRICS, rollup_metrics=ROLLUP_METRICS, background_task=True
)
@background_task(name="test_async_client")
def test_async_client(httpx, async_client, mock_server, loop, method):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    responses = loop.run_until_complete(exercise_async_client(mock_server, async_client, method))
    assert all(response.status_code == 200 for response in responses)


@pytest.mark.parametrize("distributed_tracing,span_events", ((True, True), (True, False), (False, False)))
def test_sync_cross_process_request(httpx, sync_client, mock_server, distributed_tracing, span_events):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
            "cross_application_tracer.enabled": not distributed_tracing,
        }
    )
    @validate_transaction_errors(errors=[])
    @background_task(name="test_sync_cross_process_request")
    @validate_cross_process_headers
    def _test():
        transaction = current_transaction()

        with sync_client:
            response = sync_client.get(f"http://localhost:{mock_server.port}")

        transaction._test_request_headers = response.request.headers

        assert response.status_code == 200

    _test()


@pytest.mark.parametrize("distributed_tracing,span_events", ((True, True), (True, False), (False, False)))
@validate_transaction_errors(errors=[])
@background_task(name="test_async_cross_process_request")
@validate_cross_process_headers
def test_async_cross_process_request(httpx, async_client, mock_server, loop, distributed_tracing, span_events):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    @override_application_settings(
        {"distributed_tracing.enabled": distributed_tracing, "span_events.enabled": span_events}
    )
    async def _test():
        async with async_client:
            response = await async_client.get(f"http://localhost:{mock_server.port}")

        return response

    transaction = current_transaction()
    response = loop.run_until_complete(_test())
    transaction._test_request_headers = response.request.headers

    assert response.status_code == 200


@override_application_settings(
    {"distributed_tracing.enabled": True, "span_events.enabled": True, "cross_application_tracer.enabled": True}
)
@validate_transaction_errors(errors=[])
@background_task(name="test_sync_cross_process_override_headers")
def test_sync_cross_process_override_headers(httpx, sync_client, mock_server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    transaction = current_transaction()

    with sync_client:
        response = sync_client.get(f"http://localhost:{mock_server.port}", headers={"newrelic": "1234"})

    transaction._test_request_headers = response.request.headers

    assert response.status_code == 200
    assert response.request.headers["newrelic"] == "1234"


@override_application_settings({"distributed_tracing.enabled": True, "span_events.enabled": True})
@validate_transaction_errors(errors=[])
@background_task(name="test_async_cross_process_override_headers")
def test_async_cross_process_override_headers(httpx, async_client, mock_server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    async def _test():
        async with async_client:
            response = await async_client.get(f"http://localhost:{mock_server.port}", headers={"newrelic": "1234"})

        return response

    response = loop.run_until_complete(_test())

    assert response.status_code == 200
    assert response.request.headers["newrelic"] == "1234"


@pytest.mark.parametrize("cat_enabled", [True, False])
@pytest.mark.parametrize("response_code", [200, 500])
def test_sync_client_cat_response_processing(cat_enabled, response_code, sync_client, mock_server, httpx):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = response_code

    _custom_settings = {
        "cross_process_id": "1#1",
        "encoding_key": ENCODING_KEY,
        "trusted_account_ids": [1],
        "cross_application_tracer.enabled": cat_enabled,
        "distributed_tracing.enabled": False,
        "transaction_tracer.transaction_threshold": 0.0,
    }

    expected_metrics = [
        (
            f"ExternalTransaction/localhost:{mock_server.port}/1#1/WebTransaction/Function/app:beep",
            1 if cat_enabled else None,
        )
    ]

    @validate_transaction_metrics(
        "test_sync_client_cat_response_processing",
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics,
    )
    @validate_tt_segment_params(exact_params={"http.statusCode": response_code})
    @override_application_settings(_custom_settings)
    @background_task(name="test_sync_client_cat_response_processing")
    def _test():
        with sync_client:
            response = sync_client.get(f"http://localhost:{mock_server.port}")

    _test()


@pytest.mark.parametrize("cat_enabled", [True, False])
@pytest.mark.parametrize("response_code", [200, 500])
def test_async_client_cat_response_processing(cat_enabled, response_code, httpx, async_client, mock_server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = response_code

    _custom_settings = {
        "cross_process_id": "1#1",
        "encoding_key": ENCODING_KEY,
        "trusted_account_ids": [1],
        "cross_application_tracer.enabled": cat_enabled,
        "distributed_tracing.enabled": False,
        "transaction_tracer.transaction_threshold": 0.0,
    }

    expected_metrics = [
        (
            f"ExternalTransaction/localhost:{mock_server.port}/1#1/WebTransaction/Function/app:beep",
            1 if cat_enabled else None,
        )
    ]

    @validate_transaction_metrics(
        "test_async_client_cat_response_processing",
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics,
    )
    @validate_tt_segment_params(exact_params={"http.statusCode": response_code})
    @override_application_settings(_custom_settings)
    @background_task(name="test_async_client_cat_response_processing")
    def _test():
        async def coro():
            async with async_client:
                response = await async_client.get(f"http://localhost:{mock_server.port}")

            return response

        response = loop.run_until_complete(coro())

    _test()


@dt_enabled
def test_sync_client_event_hook_exception(httpx, mock_server):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 500

    def exception_event_hook(response):
        if response.status_code >= 400:
            raise RuntimeError

    def empty_hook(response):
        pass

    @validate_span_events(
        count=1,
        exact_intrinsics={"name": f"External/localhost:{mock_server.port}/httpx/GET"},
        exact_agents={"http.statusCode": CAT_RESPONSE_CODE},
    )
    @background_task(name="test_sync_client_event_hook_exception")
    def make_request(client, exc_expected=True):
        if exc_expected:
            with pytest.raises(RuntimeError):
                client.get(f"http://localhost:{mock_server.port}")
        else:
            client.get(f"http://localhost:{mock_server.port}")

    with httpx.Client(event_hooks={"response": [exception_event_hook]}) as client:
        # Test client init
        make_request(client)

        # Test client setter
        client.event_hooks = {"response": [exception_event_hook]}
        make_request(client)

        # Test dict setitem
        client.event_hooks["response"] = [exception_event_hook]
        make_request(client)

        # Test list insert
        client.event_hooks["response"].insert(0, exception_event_hook)
        make_request(client)

        # Don't crash if response isn't specified
        client.event_hooks = {"request": [empty_hook]}
        make_request(client, exc_expected=False)


@override_application_settings({"distributed_tracing.enabled": True, "span_events.enabled": True})
def test_async_client_event_hook_exception(httpx, mock_server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 500

    def exception_event_hook(response):
        if response.status_code >= 400:
            raise RuntimeError

    def empty_hook(response):
        pass

    @validate_span_events(
        count=1,
        exact_intrinsics={"name": f"External/localhost:{mock_server.port}/httpx/GET"},
        exact_agents={"http.statusCode": CAT_RESPONSE_CODE},
    )
    @background_task(name="test_sync_client_event_hook_exception")
    def make_request(client, exc_expected=True):
        async def coro():
            if exc_expected:
                with pytest.raises(RuntimeError):
                    await client.get(f"http://localhost:{mock_server.port}")
            else:
                await client.get(f"http://localhost:{mock_server.port}")

        loop.run_until_complete(coro())

    def _test():
        with httpx.AsyncClient(event_hooks={"response": [exception_event_hook]}) as client:
            # Test client init
            make_request(client)

            # Test client setter
            client.event_hooks = {"response": [exception_event_hook]}
            make_request(client)

            # Test dict setitem
            client.event_hooks["response"] = [exception_event_hook]
            make_request(client)

            # Test list insert
            client.event_hooks["response"].insert(0, exception_event_hook)
            make_request(client)

            # Don't crash if response isn't specified
            client.event_hooks = {"request": [empty_hook]}
            make_request(client, exc_expected=False)


@override_generic_settings(global_settings(), {"enabled": False})
def test_sync_nr_disabled(httpx, mock_server):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    with httpx.Client() as client:
        trace = current_trace()
        response = client.get(f"http://localhost:{mock_server.port}")

        assert response.status_code == 200
        assert trace is None


@override_generic_settings(global_settings(), {"enabled": False})
def test_async_nr_disabled(httpx, mock_server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    async def _test():
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{mock_server.port}")

        return response

    trace = current_trace()
    response = loop.run_until_complete(_test())
    assert response.status_code == 200
    assert trace is None


@pytest.mark.parametrize("client", ("Client", "AsyncClient"))
def test_invalid_import_order_client(monkeypatch, httpx, mock_server, loop, client):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    if "Async" in client:
        is_async = True
    else:
        is_async = False

    client = getattr(httpx, client)

    # Force the client class into the state as if instrumentation had not run
    monkeypatch.setattr(client, "_event_hooks", None)

    # Instantiate a client
    client = client()

    # Remove monkeypatching of _event_hooks to restore instrumentation
    monkeypatch.undo()

    if is_async:
        responses = loop.run_until_complete(exercise_async_client(mock_server, client, "get"))
        assert all(response.status_code == 200 for response in responses)
    else:
        response = exercise_sync_client(mock_server, client, "get")
        assert response.status_code == 200


@validate_transaction_metrics(
    "test_sync_client_http2", scoped_metrics=SCOPED_METRICS, rollup_metrics=ROLLUP_METRICS, background_task=True
)
@background_task(name="test_sync_client_http2")
def test_sync_client_http2(httpx, real_server):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    client = httpx.Client(http1=False, http2=True, verify=False)
    response = exercise_sync_client(real_server, client, "get", protocol="https")

    assert response.status_code == 200
    assert response.http_version in {"HTTP/2", "HTTP/2.0"}


@validate_transaction_metrics(
    "test_async_client_http2", scoped_metrics=SCOPED_METRICS, rollup_metrics=ROLLUP_METRICS, background_task=True
)
@background_task(name="test_async_client_http2")
def test_async_client_http2(httpx, real_server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    client = httpx.AsyncClient(http1=False, http2=True, verify=False)

    responses = loop.run_until_complete(exercise_async_client(real_server, client, "get", protocol="https"))
    assert all(response.status_code == 200 for response in responses)
    assert all(response.http_version in {"HTTP/2", "HTTP/2.0"} for response in responses)
