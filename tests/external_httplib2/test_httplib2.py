import httplib2

from testing_support.fixtures import validate_transaction_metrics
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)
from testing_support.mock_external_http_server import MockExternalHTTPServer

from newrelic.agent import background_task

_test_httplib2_http_request_scoped_metrics = [
        ('External/www.example.com/httplib2/', 1)]

_test_httplib2_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_http_connection_request',
        scoped_metrics=_test_httplib2_http_request_scoped_metrics,
        rollup_metrics=_test_httplib2_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_http_connection_request():
    connection = httplib2.HTTPConnectionWithTimeout('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()

_test_httplib2_https_request_scoped_metrics = [
        ('External/www.example.com/httplib2/', 1)]

_test_httplib2_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_https_connection_request',
        scoped_metrics=_test_httplib2_https_request_scoped_metrics,
        rollup_metrics=_test_httplib2_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_https_connection_request():
    connection = httplib2.HTTPSConnectionWithTimeout('www.example.com', 443)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()

_test_httplib2_http_request_scoped_metrics = [
        ('External/localhost:8989/httplib2/', 1)]

_test_httplib2_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        ('External/localhost:8989/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_http_connection_with_port',
        scoped_metrics=_test_httplib2_http_request_scoped_metrics,
        rollup_metrics=_test_httplib2_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_http_connection_with_port():
    external = MockExternalHTTPServer()
    external.start()
    connection = httplib2.HTTPConnectionWithTimeout('localhost', 8989)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()
    external.stop()

_test_httplib2_http_request_scoped_metrics = [
        ('External/www.example.com/httplib2/', 1)]

_test_httplib2_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib2/', 1)]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_http_request',
        scoped_metrics=_test_httplib2_http_request_scoped_metrics,
        rollup_metrics=_test_httplib2_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib2_http_request():
    connection = httplib2.Http()
    response, content = connection.request('http://www.example.com', 'GET')

@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_httplib2_cross_process_request():
    connection = httplib2.HTTPConnectionWithTimeout('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()

_test_httplib2_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_httplib2_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('ExternalApp/www.example.com/1#2/all', 1),
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_httplib2_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]

@validate_transaction_metrics(
        'test_httplib2:test_httplib2_cross_process_response',
        scoped_metrics=_test_httplib2_cross_process_response_scoped_metrics,
        rollup_metrics=_test_httplib2_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_httplib2_cross_process_response_external_node_params)
@background_task()
def test_httplib2_cross_process_response():
    connection = httplib2.HTTPConnectionWithTimeout('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()
