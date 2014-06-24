import requests

from testing_support.fixtures import validate_transaction_metrics
from fixtures import (cache_outgoing_headers, cache_outgoing_headers_urllib3,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)

from newrelic.agent import background_task

_test_urlopen_http_request_scoped_metrics = [
        ('External/www.example.com/requests/', 1)]

_test_urlopen_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/requests/', 1)]

@validate_transaction_metrics(
        'test_requests:test_http_request_get',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_get():
    requests.get('http://www.example.com/')

@validate_transaction_metrics(
        'test_requests:test_https_request_get',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_https_request_get():
    requests.get('https://www.example.com/', verify=False)
