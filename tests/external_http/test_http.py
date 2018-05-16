import pytest
import six

from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings)
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)

from newrelic.api.background_task import background_task

if six.PY2:
    import httplib
    _external_metric = 'External/www.example.com/httplib/'
else:
    import http.client as httplib
    _external_metric = 'External/www.example.com/http/'

_test_http_http_request_scoped_metrics = [
        (_external_metric, 1)]

_test_http_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        (_external_metric, 1)]


@validate_transaction_metrics(
        'test_http:test_http_http_request',
        scoped_metrics=_test_http_http_request_scoped_metrics,
        rollup_metrics=_test_http_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_http_request():
    connection = httplib.HTTPConnection('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


_test_http_https_request_scoped_metrics = [
        (_external_metric, 1)]

_test_http_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        (_external_metric, 1)]


@validate_transaction_metrics(
        'test_http:test_http_https_request',
        scoped_metrics=_test_http_https_request_scoped_metrics,
        rollup_metrics=_test_http_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_https_request():
    connection = httplib.HTTPSConnection('www.example.com', 443)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


@pytest.mark.parametrize('distributed_tracing', (True, False))
def test_http_cross_process_request(distributed_tracing):

    @background_task(name='test_http:test_http_cross_process_request')
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        connection = httplib.HTTPConnection('www.example.com', 80)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    if distributed_tracing:
        _test = override_application_settings(
                {'feature_flag': set(('distributed_tracing',))})(_test)

    _test()


_test_http_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_http_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('ExternalApp/www.example.com/1#2/all', 1),
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_http_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@validate_transaction_metrics(
        'test_http:test_http_cross_process_response',
        scoped_metrics=_test_http_cross_process_response_scoped_metrics,
        rollup_metrics=_test_http_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_http_cross_process_response_external_node_params)
@background_task()
def test_http_cross_process_response():
    connection = httplib.HTTPConnection('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()
