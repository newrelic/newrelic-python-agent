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

import aiohttp
import pytest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_distributed_tracing_headers import validate_distributed_tracing_headers

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.common.package_version_utils import get_package_version_tuple

version_info = get_package_version_tuple("aiohttp")

if version_info < (2, 0):
    _expected_error_class = aiohttp.errors.HttpProcessingError
else:
    _expected_error_class = aiohttp.client_exceptions.ClientResponseError


async def fetch(url, headers=None, raise_for_status=False, connector=None):
    kwargs = {}
    if version_info >= (2, 0):
        kwargs = {"raise_for_status": raise_for_status}

    session = aiohttp.ClientSession(connector=connector, **kwargs)
    request = session._request("GET", url, headers=headers)
    headers = {}

    try:
        response = await request
        if raise_for_status and version_info < (2, 0):
            response.raise_for_status()
    except _expected_error_class:
        return headers

    response_text = await response.text()
    for header in response_text.split("\n"):
        if not header:
            continue
        try:
            h, v = header.split(":", 1)
        except ValueError:
            continue
        headers[h.strip()] = v.strip()
    f = session.close()
    await asyncio.ensure_future(f)
    return headers


@pytest.mark.parametrize("distributed_tracing", (True, False))
@pytest.mark.parametrize("span_events", (True, False))
@background_task(name="test_outbound_headers")
@validate_distributed_tracing_headers
def test_outbound_headers(event_loop, distributed_tracing, span_events, mock_header_server):
    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
        }
    )
    async def _test():
        headers = await fetch(f"http://127.0.0.1:{mock_header_server.port}")
        return headers
        
    transaction = current_transaction()
    request_headers = event_loop.run_until_complete(_test())
    transaction._test_request_headers = request_headers


def test_outbound_headers_exception(event_loop, mock_header_server):
    @background_task(name="test_outbound_headers_exception")
    async def test():
        # corrupt the transaction object to force an error
        transaction = current_transaction()
        guid = transaction.guid
        delattr(transaction, "guid")

        try:
            headers = await fetch(f"http://127.0.0.1:{mock_header_server.port}")

            assert not headers.get("newrelic")
            assert not headers.get("traceparent")
            assert not headers.get("tracestate")
        finally:
            transaction.guid = guid

    event_loop.run_until_complete(test())
