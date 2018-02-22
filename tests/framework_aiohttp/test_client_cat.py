import pytest
import asyncio
import aiohttp

from newrelic.api.background_task import background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction

from testing_support.external_fixtures import (create_incoming_headers,
        validate_external_node_params)
from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer, MockExternalHTTPServer)

version_info = tuple(int(_) for _ in aiohttp.__version__.split('.'))
xfailif_aiohttp1 = pytest.mark.xfail(version_info < (2, 0), strict=True,
        reason='PYTHON-2678')


@asyncio.coroutine
def fetch(url, headers=None, raise_for_status=False, connector=None):
    session = aiohttp.ClientSession(raise_for_status=raise_for_status,
            connector=connector)
    request = session._request('GET', url, headers=headers)
    headers = {}

    try:
        response = yield from request
    except aiohttp.client_exceptions.ClientResponseError:
        return headers

    response_text = yield from response.text()
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


@pytest.fixture(scope='module')
def mock_header_server():
    with MockExternalHTTPHResponseHeadersServer():
        yield


@xfailif_aiohttp1
@pytest.mark.parametrize('cat_enabled', [True, False])
def test_outbound_cross_process_headers(cat_enabled, mock_header_server):

    # FIXME
    if cat_enabled and version_info >= (3, 0):
        pytest.xfail('PYTHON-2672')

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


_nr_key = ExternalTrace.cat_id_key
_customer_headers_tests = [
        {'MY_CUSTOM_HEADER': 'I love cats'},
        {_nr_key: 'I love dogs'},
]


@xfailif_aiohttp1
@pytest.mark.parametrize('customer_headers', _customer_headers_tests)
@background_task()
def test_outbound_cross_process_headers_custom_headers(customer_headers,
        mock_header_server):

    loop = asyncio.get_event_loop()
    headers = loop.run_until_complete(fetch('http://localhost:8989',
        customer_headers.copy()))

    # always honor customer headers
    for expected_header, expected_value in customer_headers.items():
        assert headers.get(expected_header) == expected_value


@xfailif_aiohttp1
def test_outbound_cross_process_headers_no_txn(mock_header_server):

    loop = asyncio.get_event_loop()
    headers = loop.run_until_complete(fetch('http://localhost:8989'))

    assert not headers.get(ExternalTrace.cat_id_key)
    assert not headers.get(ExternalTrace.cat_transaction_key)


@xfailif_aiohttp1
@background_task()
def test_outbound_cross_process_headers_exception(mock_header_server):

    # corrupt the transaction object to force an error
    transaction = current_transaction()
    guid = transaction.guid
    delattr(transaction, 'guid')

    try:
        loop = asyncio.get_event_loop()
        headers = loop.run_until_complete(fetch('http://localhost:8989'))

        assert not headers.get(ExternalTrace.cat_id_key)
        assert not headers.get(ExternalTrace.cat_transaction_key)
    finally:
        transaction.guid = guid


class PoorResolvingConnector(aiohttp.TCPConnector):
    @asyncio.coroutine
    def _resolve_host(self, host, port):
        res = [{'hostname': host, 'host': host, 'port': 1234,
                 'family': self._family, 'proto': 0, 'flags': 0}]
        hosts = yield from super(PoorResolvingConnector,
                self)._resolve_host(host, port)
        for hinfo in hosts:
            res.append(hinfo)
        return res


@xfailif_aiohttp1
@pytest.mark.parametrize('cat_enabled', [True, False])
@pytest.mark.parametrize('response_code', [200, 404])
@pytest.mark.parametrize('raise_for_status', [True, False])
@pytest.mark.parametrize('connector_class',
        [None, PoorResolvingConnector])  # None will use default
def test_process_incoming_headers(cat_enabled, response_code,
        raise_for_status, connector_class):

    # FIXME
    if connector_class and version_info >= (3, 0):
        pytest.xfail('PYTHON-2672')

    # It was discovered via packnsend that the `throw` method of the `_request`
    # coroutine is used in the case of poorly resolved hosts. An older version
    # of the instrumentation ended the ExternalTrace anytime `throw` was called
    # which meant that incoming CAT headers were never processed. The
    # `PoorResolvingConnector` connector in this test ensures that `throw` is
    # always called and thus makes sure the trace is not ended before
    # StopIteration is called.

    _test_cross_process_response_scoped_metrics = [
            ('ExternalTransaction/localhost:8990/1#2/test', 1 if cat_enabled
                else None)]

    _test_cross_process_response_rollup_metrics = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:8990/all', 1),
            ('ExternalApp/localhost:8990/1#2/all', 1 if cat_enabled else None),
            ('ExternalTransaction/localhost:8990/1#2/test', 1 if cat_enabled
                else None)]

    _test_cross_process_response_external_node_params = [
            ('cross_process_id', '1#2'),
            ('external_txn_name', 'test'),
            ('transaction_guid', '0123456789012345')]

    _test_cross_process_response_external_node_forgone_params = [
            k for k, v in _test_cross_process_response_external_node_params]

    connector = connector_class() if connector_class else None

    @override_application_settings(
            {'cross_application_tracer.enabled': cat_enabled})
    @validate_transaction_metrics(
            'test_client_cat:test_process_incoming_headers.<locals>.task_test',
            scoped_metrics=_test_cross_process_response_scoped_metrics,
            rollup_metrics=_test_cross_process_response_rollup_metrics,
            background_task=True)
    @validate_external_node_params(
            params=(_test_cross_process_response_external_node_params if
                cat_enabled else []),
            forgone_params=([] if cat_enabled else
                _test_cross_process_response_external_node_forgone_params))
    @background_task()
    def task_test():
        transaction = current_transaction()
        headers = create_incoming_headers(transaction)

        def respond_with_cat_header(self):
            self.send_response(response_code)
            for header, value in headers:
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(b'')

        with MockExternalHTTPServer(handler=respond_with_cat_header,
                port=8990):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(fetch('http://localhost:8990',
                raise_for_status=raise_for_status, connector=connector))

    task_test()
