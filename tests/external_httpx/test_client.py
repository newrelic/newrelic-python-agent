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
from testing_support.fixtures import (
    override_application_settings,
    validate_transaction_errors,
    validate_transaction_metrics,
    validate_tt_segment_params,
    override_application_settings
)
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers,
)

from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task
from testing_support.mock_external_http_server import (
    MockExternalHTTPHResponseHeadersServer)


ENCODING_KEY = '1234567890123456789012345678901234567890'
SCOPED_METRICS = []
ROLLUP_METRICS = [("External/all", 2), ("External/allOther", 2)]

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
    cat_response_header = ('X-NewRelic-App-Data',
            'ahACFwQUGxpuVVNmQVVbRVZbTVleXBxyQFhUTFBfXx1SREUMV'
            'V1cQBMeAxgEGAULFR0AHhFQUQJWAAgAUwVQVgJQDgsOEh1UUlhGU2o=')
    self.send_response(CAT_RESPONSE_CODE)
    self.send_header(*cat_response_header)
    self.end_headers()
    self.wfile.write(b'Example Data')


@pytest.fixture(scope='session')
def server():
    external = MockExternalHTTPHResponseHeadersServer(handler=cat_response_handler)
    with external:
        yield external


@pytest.fixture()
def populate_metrics(server, request):
    SCOPED_METRICS[:] = []
    method = request.getfixturevalue("method").upper()
    SCOPED_METRICS.append(("External/localhost:%d/httpx/%s" % (server.port, method), 2))


@pytest.mark.parametrize(
    "method",
    (
        "get",
        "options",
        "head",
        "post",
        "put",
        "patch",
        "delete",
    ),
)
@validate_transaction_metrics(
    "test_sync_client",
    scoped_metrics=SCOPED_METRICS,
    rollup_metrics=ROLLUP_METRICS,
    background_task=True,
)
@background_task(name='test_sync_client')
def test_sync_client(httpx, server, method):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    with httpx.Client() as client:
        resolved_method = getattr(client, method)
        resolved_method("http://localhost:%s" % server.port)
        response = resolved_method("http://localhost:%s" % server.port)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "method",
    (
        "get",
        "options",
        "head",
        "post",
        "put",
        "patch",
        "delete",
    ),
)
@validate_transaction_metrics(
    "test_async_client",
    scoped_metrics=SCOPED_METRICS,
    rollup_metrics=ROLLUP_METRICS,
    background_task=True,
)
@background_task(name='test_async_client')
def test_async_client(httpx, server, loop, method):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = 200

    async def test_async_client():
        async with httpx.AsyncClient() as client:
            resolved_method = getattr(client, method)
            responses = await asyncio.gather(
                resolved_method("http://localhost:%s" % server.port),
                resolved_method("http://localhost:%s" % server.port),
            )

        return responses

    responses = loop.run_until_complete(test_async_client())
    assert all(response.status_code == 200 for response in responses)


@pytest.mark.parametrize(
    "distributed_tracing,span_events",
    (
        (True, True),
        (True, False),
        (False, False),
    ),
)
def test_sync_cross_process_request(httpx, server, distributed_tracing, span_events):
    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
        }
    )
    @validate_transaction_errors(errors=[])
    @background_task(name="test_sync_cross_process_request")
    @validate_cross_process_headers
    def _test():
        transaction = current_transaction()

        with httpx.Client() as client:
            response = client.get("http://localhost:%s" % server.port)

        transaction._test_request_headers = response.request.headers

        assert response.status_code == 200

    _test()


@pytest.mark.parametrize(
    "distributed_tracing,span_events",
    (
        (True, True),
        (True, False),
        (False, False),
    ),
)
@validate_transaction_errors(errors=[])
@background_task(name="test_async_cross_process_request")
@validate_cross_process_headers
def test_async_cross_process_request(
    httpx, server, loop, distributed_tracing, span_events
):
    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
        }
    )
    async def _test():
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:%s" % server.port)

        return response

    transaction = current_transaction()
    response = loop.run_until_complete(_test())
    transaction._test_request_headers = response.request.headers

    assert response.status_code == 200


@override_application_settings(
    {
        "distributed_tracing.enabled": True,
        "span_events.enabled": True,
    }
)
@validate_transaction_errors(errors=[])
@background_task(name="test_sync_cross_process_override_headers")
def test_sync_cross_process_override_headers(httpx, server, loop):
    transaction = current_transaction()

    with httpx.Client() as client:
        response = client.get(
            "http://localhost:%s" % server.port, headers={"newrelic": "1234"}
        )

    transaction._test_request_headers = response.request.headers

    assert response.status_code == 200
    assert response.request.headers["newrelic"] == "1234"


@override_application_settings(
    {
        "distributed_tracing.enabled": True,
        "span_events.enabled": True,
    }
)
@validate_transaction_errors(errors=[])
@background_task(name="test_async_cross_process_override_headers")
def test_async_cross_process_override_headers(httpx, server, loop):
    async def _test():
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:%s" % server.port, headers={"newrelic": "1234"}
            )

        return response

    response = loop.run_until_complete(_test())

    assert response.status_code == 200
    assert response.request.headers["newrelic"] == "1234"


@pytest.mark.parametrize('cat_enabled', [True, False])
@pytest.mark.parametrize('response_code', [200, 500])
def test_sync_client_cat_response_processing(cat_enabled, response_code, server, httpx):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = response_code

    _custom_settings = {
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'cross_application_tracer.enabled': cat_enabled,
        'distributed_tracing.enabled': False,
        'transaction_tracer.transaction_threshold': 0.0,
    }

    expected_metrics = [
        ('ExternalTransaction/localhost:%s/1#1/WebTransaction/'
                'Function/app:beep' % server.port, 1 if cat_enabled else None),
    ]

    @validate_transaction_metrics(
        'test_sync_client_cat_response_processing',
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics
    )
    @validate_tt_segment_params(exact_params={'http.statusCode': response_code})
    @override_application_settings(_custom_settings)
    @background_task(name='test_sync_client_cat_response_processing')
    def _test():
        with httpx.Client() as client:
            response = client.get("http://localhost:%s" % server.port)

    _test()


@pytest.mark.parametrize('cat_enabled', [True, False])
@pytest.mark.parametrize('response_code', [200, 500])
def test_async_client_cat_response_processing(cat_enabled, response_code, httpx, server, loop):
    global CAT_RESPONSE_CODE
    CAT_RESPONSE_CODE = response_code

    _custom_settings = {
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'cross_application_tracer.enabled': cat_enabled,
        'distributed_tracing.enabled': False,
        'transaction_tracer.transaction_threshold': 0.0,
    }

    expected_metrics = [
        ('ExternalTransaction/localhost:%s/1#1/WebTransaction/'
                'Function/app:beep' % server.port, 1 if cat_enabled else None),
    ]

    expected_metrics = []

    @validate_transaction_metrics(
        'test_async_client_cat_response_processing',
        background_task=True,
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics
    )
    @validate_tt_segment_params(exact_params={'http.statusCode': response_code})
    @override_application_settings(_custom_settings)
    @background_task(name='test_async_client_cat_response_processing')
    def _test():
        async def coro():
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:%s" % server.port)

            return response

        response = loop.run_until_complete(coro())

    _test()
