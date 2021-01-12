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
from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics


SCOPED_METRICS = []
ROLLUP_METRICS = [("External/all", 2), ("External/allOther", 2)]


@pytest.fixture(autouse=True)
def populate_metrics(server, request):
    SCOPED_METRICS[:] = []
    method = request.getfixturevalue("method").upper()
    SCOPED_METRICS.append(('External/localhost:%d/httpx/%s' % (server.port, method), 2))


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
@validate_transaction_metrics('test_sync_client',
    scoped_metrics=SCOPED_METRICS,
    rollup_metrics=ROLLUP_METRICS,
    background_task=True,
)
@background_task(name='test_sync_client')
def test_sync_client(httpx, server, method):
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
@validate_transaction_metrics('test_async_client',
    scoped_metrics=SCOPED_METRICS,
    rollup_metrics=ROLLUP_METRICS,
    background_task=True,
)
@background_task(name='test_async_client')
def test_async_client(httpx, server, loop, method):
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
