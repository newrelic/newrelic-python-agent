import os

try:
    import urllib.request as urllib2
except:
    import urllib2

from testing_support.fixtures import validate_transaction_metrics
from fixtures import (cache_outgoing_headers, validate_cross_process_headers,
    insert_incoming_headers, validate_external_node_params)

from newrelic.agent import background_task

_test_urlopen_http_request_scoped_metrics = [
        ('External/www.example.com/urllib2/', 1)]

_test_urlopen_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib2/', 1)]

@validate_transaction_metrics(
        'test_urllib2:test_urlopen_http_request',
        scoped_metrics=_test_urlopen_http_request_scoped_metrics,
        rollup_metrics=_test_urlopen_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlopen_http_request():
    urllib2.urlopen('http://www.example.com/')

_test_urlopen_https_request_scoped_metrics = [
        ('External/www.example.com/urllib2/', 1)]

_test_urlopen_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/urllib2/', 1)]

@validate_transaction_metrics(
        'test_urllib2:test_urlopen_https_request',
        scoped_metrics=_test_urlopen_https_request_scoped_metrics,
        rollup_metrics=_test_urlopen_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlopen_https_request():
    urllib2.urlopen('https://www.example.com/')

@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_urlopen_cross_process_request():
    urllib2.urlopen('http://www.example.com/')

_test_urlopen_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_urlopen_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('ExternalApp/www.example.com/1#2/all', 1),
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_urlopen_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]

@validate_transaction_metrics(
        'test_urllib2:test_urlopen_cross_process_response',
        scoped_metrics=_test_urlopen_cross_process_response_scoped_metrics,
        rollup_metrics=_test_urlopen_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_urlopen_cross_process_response_external_node_params)
@background_task()
def test_urlopen_cross_process_response():
    urllib2.urlopen('http://www.example.com/')
