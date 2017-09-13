import pytest
import asyncio
import aiohttp.client

from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)
from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace


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


@background_task()
def test_outbound_cross_process_headers(mock_header_server):
    loop = asyncio.get_event_loop()
    headers = loop.run_until_complete(fetch('http://localhost:8989'))

    transaction = current_transaction()
    expected_headers = ExternalTrace.generate_request_headers(transaction)

    for expected_header, expected_value in expected_headers:
        assert headers.get(expected_header) == expected_value
