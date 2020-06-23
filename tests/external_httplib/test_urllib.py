import os

try:
    import urllib.request as urllib
except:
    import urllib

from testing_support.fixtures import validate_transaction_metrics
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)

from newrelic.api.background_task import background_task


_test_urlopener_http_request_scoped_metrics = [
        ('External/www.example.com/urllib/', 1)]


_test_urlopener_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib/', 1)]


@validate_transaction_metrics(
        'test_urllib:test_urlopener_http_request',
        scoped_metrics=_test_urlopener_http_request_scoped_metrics,
        rollup_metrics=_test_urlopener_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlopener_http_request():
    opener = urllib.URLopener()
    opener.open('http://www.example.com/')


_test_urlopener_https_request_scoped_metrics = [
        ('External/www.example.com/urllib/', 1)]

_test_urlopener_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib/', 1)]


@validate_transaction_metrics(
        'test_urllib:test_urlopener_https_request',
        scoped_metrics=_test_urlopener_https_request_scoped_metrics,
        rollup_metrics=_test_urlopener_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlopener_https_request():
    opener = urllib.URLopener()
    opener.open('https://www.example.com/')


def test_urlopener_http_request_with_port(server):
    scoped = [
            ('External/localhost:%d/urllib/' % server.port, 1)]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            ('External/localhost:%d/urllib/' % server.port, 1)]

    @validate_transaction_metrics(
            'test_urllib:test_urlopener_http_request_with_port',
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @background_task(name='test_urllib:test_urlopener_http_request_with_port')
    def _test():
        opener = urllib.URLopener()
        opener.open('http://localhost:%d/' % server.port)

    _test()


_test_urlopener_file_request_scoped_metrics = [
        ('External/unknown/urllib/', None)]

_test_urlopener_file_request_rollup_metrics = [
        ('External/all', None),
        ('External/allOther', None),
        ('External/unknown/urllib/', None)]


@validate_transaction_metrics(
        'test_urllib:test_urlopener_file_request',
        scoped_metrics=_test_urlopener_file_request_scoped_metrics,
        rollup_metrics=_test_urlopener_file_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlopener_file_request():
    filename = os.path.join('file://', __file__)
    opener = urllib.URLopener()
    opener.open(filename)


@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_urlopener_cross_process_request():
    opener = urllib.URLopener()
    opener.open('http://www.example.com/')


_test_urlopener_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_urlopener_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('ExternalApp/www.example.com/1#2/all', 1),
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_urlopener_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@validate_transaction_metrics(
        'test_urllib:test_urlopener_cross_process_response',
        scoped_metrics=_test_urlopener_cross_process_response_scoped_metrics,
        rollup_metrics=_test_urlopener_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_urlopener_cross_process_response_external_node_params)
@background_task()
def test_urlopener_cross_process_response():
    opener = urllib.URLopener()
    opener.open('http://www.example.com/')


_test_urlretrieve_http_request_scoped_metrics = [
        ('External/www.example.com/urllib/', 1)]

_test_urlretrieve_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib/', 1)]


@validate_transaction_metrics(
        'test_urllib:test_urlretrieve_http_request',
        scoped_metrics=_test_urlretrieve_http_request_scoped_metrics,
        rollup_metrics=_test_urlretrieve_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlretrieve_http_request():
    urllib.urlretrieve('http://www.example.com/')


_test_urlretrieve_https_request_scoped_metrics = [
        ('External/www.example.com/urllib/', 1)]

_test_urlretrieve_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib/', 1)]


@validate_transaction_metrics(
        'test_urllib:test_urlretrieve_https_request',
        scoped_metrics=_test_urlretrieve_https_request_scoped_metrics,
        rollup_metrics=_test_urlretrieve_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlretrieve_https_request():
    urllib.urlretrieve('https://www.example.com/')


@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_urlretrieve_cross_process_request():
    urllib.urlretrieve('http://www.example.com/')


_test_urlretrieve_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_urlretrieve_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('ExternalApp/www.example.com/1#2/all', 1),
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_urlretrieve_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@validate_transaction_metrics(
        'test_urllib:test_urlretrieve_cross_process_response',
        scoped_metrics=_test_urlretrieve_cross_process_response_scoped_metrics,
        rollup_metrics=_test_urlretrieve_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_urlretrieve_cross_process_response_external_node_params)
@background_task()
def test_urlretrieve_cross_process_response():
    urllib.urlretrieve('http://www.example.com/')
