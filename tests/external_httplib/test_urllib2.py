# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import os

try:
    import urllib.request as urllib2
except:
    import urllib2

from testing_support.fixtures import validate_transaction_metrics
from testing_support.external_fixtures import (cache_outgoing_headers,
    insert_incoming_headers)
from testing_support.validators.validate_external_node_params import (
    validate_external_node_params)
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers)

from newrelic.api.background_task import background_task


@pytest.fixture(scope='session')
def metrics(server):
    scoped = [
            ('External/localhost:%d/urllib2/' % server.port, 1)]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            ('External/localhost:%d/urllib2/' % server.port, 1)]

    return scoped, rollup


def test_urlopen_http_request(server, metrics):
    @validate_transaction_metrics(
            'test_urllib2:test_urlopen_http_request',
            scoped_metrics=metrics[0],
            rollup_metrics=metrics[1],
            background_task=True)
    @background_task(name='test_urllib2:test_urlopen_http_request')
    def _test():
        urllib2.urlopen('http://localhost:%d/' % server.port)

    _test()


def test_urlopen_https_request(server, metrics):
    @validate_transaction_metrics(
            'test_urllib2:test_urlopen_https_request',
            scoped_metrics=metrics[0],
            rollup_metrics=metrics[1],
            background_task=True)
    @background_task(name='test_urllib2:test_urlopen_https_request')
    def _test():
        try:
            urllib2.urlopen('https://localhost:%d/' % server.port)
        except Exception:
            pass

    _test()


def test_urlopen_http_request_with_port(server):
    scoped = [
            ('External/localhost:%d/urllib2/' % server.port, 1)]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            ('External/localhost:%d/urllib2/' % server.port, 1)]

    @validate_transaction_metrics(
            'test_urllib2:test_urlopen_http_request_with_port',
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @background_task(name='test_urllib2:test_urlopen_http_request_with_port')
    def _test():
        urllib2.urlopen('http://localhost:%d/' % server.port)

    _test()


_test_urlopen_file_request_scoped_metrics = [
        ('External/unknown/urllib2/', None)]

_test_urlopen_file_request_rollup_metrics = [
        ('External/all', None),
        ('External/allOther', None),
        ('External/unknown/urllib2/', None)]


@validate_transaction_metrics(
        'test_urllib2:test_urlopen_file_request',
        scoped_metrics=_test_urlopen_file_request_scoped_metrics,
        rollup_metrics=_test_urlopen_file_request_rollup_metrics,
        background_task=True)
@background_task()
def test_urlopen_file_request():
    path = os.path.abspath(__file__)
    file_uri = 'file://%s' % path
    urllib2.urlopen(file_uri)


@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_urlopen_cross_process_request(server):
    urllib2.urlopen('http://localhost:%d/' % server.port)


def test_urlopen_cross_process_response(server):
    _test_urlopen_cross_process_response_scoped_metrics = [
            ('ExternalTransaction/localhost:%d/1#2/test' % server.port, 1)]

    _test_urlopen_cross_process_response_rollup_metrics = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            ('ExternalApp/localhost:%d/1#2/all' % server.port, 1),
            ('ExternalTransaction/localhost:%d/1#2/test' % server.port, 1)]

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
    @background_task(name='test_urllib2:test_urlopen_cross_process_response')
    def _test():
        urllib2.urlopen('http://localhost:%d/' % server.port)

    _test()
