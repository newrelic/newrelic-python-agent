import pytest
import asyncio
import aiohttp.client

from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction

from testing_support.fixtures import override_application_settings
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)


@asyncio.coroutine
def fetch(url):
    session = aiohttp.client.ClientSession()
    request = session._request('GET', url)
    response = yield from request
    response_text = yield from response.text()
    headers = {}
    for header in response_text.split('\n'):
        if not header:
            continue
        try:
            h, v = header.split(':', 1)
        except ValueError:
            continue
        headers[h.strip()] = v.strip()
    session.close()
    return headers


@pytest.fixture()
def mock_header_server():
    with MockExternalHTTPHResponseHeadersServer():
        yield


@pytest.mark.parametrize('cat_enabled', [True, False])
def test_outbound_cross_process_headers(cat_enabled, mock_header_server):

    @override_application_settings(
            {'cross_application_tracer.enabled': cat_enabled})
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        headers = loop.run_until_complete(fetch('http://localhost:8989'))

        transaction = current_transaction()
        expected_headers = ExternalTrace.generate_request_headers(transaction)

        for expected_header, expected_value in expected_headers:
            assert headers.get(expected_header) == expected_value

        if not cat_enabled:
            assert not headers.get(ExternalTrace.cat_id_key)
            assert not headers.get(ExternalTrace.cat_transaction_key)

    task_test()
