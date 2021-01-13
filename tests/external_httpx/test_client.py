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
)
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

SCOPED_METRICS = []
ROLLUP_METRICS = [("External/all", 2), ("External/allOther", 2)]


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
@background_task(name="test_sync_client")
def test_sync_client(httpx, server, method, populate_metrics):
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
@background_task(name="test_async_client")
def test_async_client(httpx, server, loop, method, populate_metrics):
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
    @background_task()
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
@background_task()
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
