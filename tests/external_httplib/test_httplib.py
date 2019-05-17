import pytest
try:
    import http.client as httplib
except ImportError:
    import httplib

from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings)
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)
from testing_support.mock_external_http_server import MockExternalHTTPServer

from newrelic.api.background_task import background_task
from newrelic.packages import six


def select_python_version(py2, py3):
    return six.PY3 and py3 or py2


_test_httplib_http_request_scoped_metrics = [select_python_version(
        py2=('External/www.example.com/httplib/', 1),
        py3=('External/www.example.com/http/', 1))]


_test_httplib_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        select_python_version(py2=('External/www.example.com/httplib/', 1),
                              py3=('External/www.example.com/http/', 1))]


@validate_transaction_metrics(
        'test_httplib:test_httplib_http_request',
        scoped_metrics=_test_httplib_http_request_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib_http_request():
    connection = httplib.HTTPConnection('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


@validate_transaction_metrics(
        'test_httplib:test_httplib_https_request',
        scoped_metrics=_test_httplib_http_request_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib_https_request():
    connection = httplib.HTTPSConnection('www.example.com', 443)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


_test_httplib_http_request_with_port_scoped_metrics = [select_python_version(
        py2=('External/localhost:8989/httplib/', 1),
        py3=('External/localhost:8989/http/', 1))]


_test_httplib_http_request_with_port_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        select_python_version(py2=('External/localhost:8989/httplib/', 1),
                              py3=('External/localhost:8989/http/', 1))]


@validate_transaction_metrics(
        'test_httplib:test_httplib_http_with_port_request',
        scoped_metrics=_test_httplib_http_request_with_port_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_with_port_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib_http_with_port_request():
    with MockExternalHTTPServer():
        connection = httplib.HTTPConnection('localhost', 8989)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()


@pytest.mark.parametrize('distributed_tracing,span_events', (
    (True, True),
    (True, False),
    (False, False),
))
def test_httplib_cross_process_request(distributed_tracing, span_events):
    @background_task(name='test_httplib:test_httplib_cross_process_request')
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        connection = httplib.HTTPConnection('www.example.com', 80)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    _test = override_application_settings({
        'distributed_tracing.enabled': distributed_tracing,
        'span_events.enabled': span_events,
    })(_test)

    _test()


_test_httplib_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/localhost:8989/1#2/test', 1)]


_test_httplib_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        ('ExternalApp/localhost:8989/1#2/all', 1),
        ('ExternalTransaction/localhost:8989/1#2/test', 1)]


_test_httplib_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@validate_transaction_metrics(
        'test_httplib:test_httplib_cross_process_response',
        scoped_metrics=_test_httplib_cross_process_response_scoped_metrics,
        rollup_metrics=_test_httplib_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_httplib_cross_process_response_external_node_params)
@background_task()
def test_httplib_cross_process_response():
    with MockExternalHTTPServer():
        connection = httplib.HTTPConnection('localhost', 8989)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()


def test_httplib_multiple_requests_cross_process_response():
    with MockExternalHTTPServer():
        connection = httplib.HTTPConnection('localhost', 8989)

        @validate_transaction_metrics(
                'test_httplib:test_transaction',
                scoped_metrics=_test_httplib_cross_process_response_scoped_metrics,
                rollup_metrics=_test_httplib_cross_process_response_rollup_metrics,
                background_task=True)
        @insert_incoming_headers
        @validate_external_node_params(
                params=_test_httplib_cross_process_response_external_node_params)
        @background_task(name='test_httplib:test_transaction')
        def test_transaction():
            connection.request('GET', '/')
            response = connection.getresponse()
            response.read()

        # make multiple requests with the same connection
        for _ in range(2):
            test_transaction()

        connection.close()
