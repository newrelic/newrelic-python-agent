import os
import random

import http.client as httplib

from testing_support.fixtures import validate_transaction_metrics
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)

from newrelic.agent import background_task

_test_http_http_request_scoped_metrics = [
        ('External/www.example.com/httplib/', 1)]

_test_http_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib/', 1)]

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
    data = response.read()
    connection.close()

_test_http_https_request_scoped_metrics = [
        ('External/www.example.com/httplib/', 1)]

_test_http_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/httplib/', 1)]

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
    data = response.read()
    connection.close()

@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_http_cross_process_request():
    connection = httplib.HTTPConnection('www.example.com', 80)
    connection.request('GET', '/')
    response = connection.getresponse()
    data = response.read()
    connection.close()

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
    data = response.read()
    connection.close()
