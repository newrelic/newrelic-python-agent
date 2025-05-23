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
from testing_support.external_fixtures import create_incoming_headers
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_cross_process_headers import validate_cross_process_headers
from testing_support.validators.validate_external_node_params import validate_external_node_params
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction

version_info = tuple(int(_) for _ in aiohttp.__version__.split(".")[:2])

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


@pytest.mark.parametrize("cat_enabled", (True, False))
@pytest.mark.parametrize("distributed_tracing", (True, False))
@pytest.mark.parametrize("span_events", (True, False))
def test_outbound_cross_process_headers(event_loop, cat_enabled, distributed_tracing, span_events, mock_header_server):
    @background_task(name="test_outbound_cross_process_headers")
    async def _test():
        headers = await fetch(f"http://127.0.0.1:{mock_header_server.port}")

        transaction = current_transaction()
        transaction._test_request_headers = headers

        if distributed_tracing:
            assert "newrelic" in headers
        elif cat_enabled:
            assert ExternalTrace.cat_id_key in headers
            assert ExternalTrace.cat_transaction_key in headers
        else:
            assert "newrelic" not in headers
            assert ExternalTrace.cat_id_key not in headers
            assert ExternalTrace.cat_transaction_key not in headers

        def _validate():
            pass

        if cat_enabled or distributed_tracing:
            _validate = validate_cross_process_headers(_validate)

        _validate()

    @override_application_settings(
        {
            "cross_application_tracer.enabled": cat_enabled,
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
        }
    )
    def test():
        event_loop.run_until_complete(_test())

    test()


_nr_key = ExternalTrace.cat_id_key
_customer_headers_tests = [{"Test-Header": "Test Data 1"}, {_nr_key.title(): "Test Data 2"}]


@pytest.mark.parametrize("customer_headers", _customer_headers_tests)
def test_outbound_cross_process_headers_custom_headers(event_loop, customer_headers, mock_header_server):
    headers = event_loop.run_until_complete(
        background_task()(fetch)(f"http://127.0.0.1:{mock_header_server.port}", customer_headers.copy())
    )

    # always honor customer headers
    for expected_header, expected_value in customer_headers.items():
        assert headers.get(expected_header) == expected_value


def test_outbound_cross_process_headers_no_txn(event_loop, mock_header_server):
    headers = event_loop.run_until_complete(fetch(f"http://127.0.0.1:{mock_header_server.port}"))

    assert not headers.get(ExternalTrace.cat_id_key)
    assert not headers.get(ExternalTrace.cat_transaction_key)


def test_outbound_cross_process_headers_exception(event_loop, mock_header_server):
    @background_task(name="test_outbound_cross_process_headers_exception")
    async def test():
        # corrupt the transaction object to force an error
        transaction = current_transaction()
        guid = transaction.guid
        delattr(transaction, "guid")

        try:
            headers = await fetch(f"http://127.0.0.1:{mock_header_server.port}")

            assert not headers.get(ExternalTrace.cat_id_key)
            assert not headers.get(ExternalTrace.cat_transaction_key)
        finally:
            transaction.guid = guid

    event_loop.run_until_complete(test())


class PoorResolvingConnector(aiohttp.TCPConnector):
    async def _resolve_host(self, host, port, *args, **kwargs):
        res = [{"hostname": host, "host": host, "port": 1234, "family": self._family, "proto": 0, "flags": 0}]
        hosts = await super()._resolve_host(host, port, *args, **kwargs)
        res.extend(hosts)
        return res


@pytest.mark.parametrize("cat_enabled", [True, False])
@pytest.mark.parametrize("response_code", [200, 404])
@pytest.mark.parametrize("raise_for_status", [True, False])
@pytest.mark.parametrize("connector_class", [None, PoorResolvingConnector])  # None will use default
def test_process_incoming_headers(
    event_loop, cat_enabled, response_code, raise_for_status, connector_class, mock_external_http_server
):
    # It was discovered via packnsend that the `throw` method of the `_request`
    # coroutine is used in the case of poorly resolved hosts. An older version
    # of the instrumentation ended the ExternalTrace anytime `throw` was called
    # which meant that incoming CAT headers were never processed. The
    # `PoorResolvingConnector` connector in this test ensures that `throw` is
    # always called and thus makes sure the trace is not ended before
    # StopIteration is called.
    server, response_values = mock_external_http_server
    address = f"http://127.0.0.1:{server.port}"
    port = server.port

    _test_cross_process_response_scoped_metrics = [
        (f"ExternalTransaction/127.0.0.1:{port}/1#2/test", 1 if cat_enabled else None)
    ]

    _test_cross_process_response_rollup_metrics = [
        ("External/all", 1),
        ("External/allOther", 1),
        (f"External/127.0.0.1:{port}/all", 1),
        (f"ExternalApp/127.0.0.1:{port}/1#2/all", 1 if cat_enabled else None),
        (f"ExternalTransaction/127.0.0.1:{port}/1#2/test", 1 if cat_enabled else None),
    ]

    _test_cross_process_response_external_node_params = [
        ("cross_process_id", "1#2"),
        ("external_txn_name", "test"),
        ("transaction_guid", "0123456789012345"),
    ]

    _test_cross_process_response_external_node_forgone_params = [
        k for k, v in _test_cross_process_response_external_node_params
    ]

    @background_task(name="test_process_incoming_headers")
    async def _test():
        transaction = current_transaction()
        headers = create_incoming_headers(transaction)

        response_values.append((headers, response_code))

        connector = connector_class() if connector_class else None

        await fetch(address, raise_for_status=raise_for_status, connector=connector)

    @override_application_settings(
        {"cross_application_tracer.enabled": cat_enabled, "distributed_tracing.enabled": False}
    )
    @validate_transaction_metrics(
        "test_process_incoming_headers",
        scoped_metrics=_test_cross_process_response_scoped_metrics,
        rollup_metrics=_test_cross_process_response_rollup_metrics,
        background_task=True,
    )
    @validate_external_node_params(
        params=(_test_cross_process_response_external_node_params if cat_enabled else []),
        forgone_params=([] if cat_enabled else _test_cross_process_response_external_node_forgone_params),
    )
    def test():
        event_loop.run_until_complete(_test())

    test()
