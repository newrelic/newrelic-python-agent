import urllib3

from testing_support.fixtures import validate_transaction_metrics
from fixtures import (cache_outgoing_headers, validate_cross_process_headers,
    insert_incoming_headers, validate_external_node_params)

from newrelic.agent import background_task

_test_urlopen_http_request_scoped_metrics = [
        ('External/www.example.com/urllib3/', 1)]

_test_urlopen_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib3/', 1)]

@validate_transaction_metrics(
        'test_urllib3:test_http_request_connection_pool_urlopen',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_connection_pool_urlopen():
    pool = urllib3.HTTPConnectionPool('www.example.com')
    pool.urlopen('GET', '/index.html')

@validate_transaction_metrics(
        'test_urllib3:test_http_request_connection_pool_request',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_connection_pool_request():
    pool = urllib3.HTTPConnectionPool('www.example.com')
    pool.request('GET', '/index.html')

@validate_transaction_metrics(
        'test_urllib3:test_http_request_connection_from_url_request',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_connection_from_url_request():
    conn = urllib3.connection_from_url('www.example.com')
    conn.request('GET', '/index.html')

@validate_transaction_metrics(
        'test_urllib3:test_http_request_pool_manager_urlopen',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_pool_manager_urlopen():
    pool = urllib3.PoolManager(5)
    pool.urlopen('GET', 'http://www.example.com/index.html')

@validate_transaction_metrics(
        'test_urllib3:test_https_request_connection_pool_urlopen',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_https_request_connection_pool_urlopen():
    pool = urllib3.HTTPSConnectionPool('www.example.com')
    pool.urlopen('GET', '/index.html')

@validate_transaction_metrics(
        'test_urllib3:test_https_request_connection_pool_request',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_https_request_connection_pool_request():
    pool = urllib3.HTTPSConnectionPool('www.example.com')
    pool.request('GET', '/index.html')
