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
try:
    import http.client as httplib
except ImportError:
    import httplib

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings, validate_tt_segment_params)
from testing_support.validators.validate_span_events import (
    validate_span_events)
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers)
from testing_support.validators.validate_external_node_params import (
    validate_external_node_params)
from testing_support.external_fixtures import (cache_outgoing_headers,
    insert_incoming_headers)

from newrelic.common.encoding_utils import DistributedTracePayload
from newrelic.api.background_task import background_task
from newrelic.packages import six


def select_python_version(py2, py3):
    return six.PY3 and py3 or py2


def test_httplib_http_request(server):
    scoped = [select_python_version(
            py2=('External/localhost:%d/httplib/' % server.port, 1),
            py3=('External/localhost:%d/http/' % server.port, 1))]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            select_python_version(py2=('External/localhost:%d/httplib/' % server.port, 1),
                                py3=('External/localhost:%d/http/' % server.port, 1))]

    @validate_transaction_metrics(
            'test_httplib:test_httplib_http_request',
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @background_task(name='test_httplib:test_httplib_http_request')
    def _test():
        connection = httplib.HTTPConnection('localhost', server.port)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    _test()


def test_httplib_https_request(server):
    _test_httplib_https_request_scoped_metrics = [select_python_version(
            py2=('External/localhost:%d/httplib/' % server.port, 1),
            py3=('External/localhost:%d/http/' % server.port, 1))]


    _test_httplib_https_request_rollup_metrics = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            select_python_version(py2=('External/localhost:%d/httplib/' % server.port, 1),
                                py3=('External/localhost:%d/http/' % server.port, 1))]


    @validate_transaction_metrics(
            'test_httplib:test_httplib_https_request',
            scoped_metrics=_test_httplib_https_request_scoped_metrics,
            rollup_metrics=_test_httplib_https_request_rollup_metrics,
            background_task=True)
    @background_task(name='test_httplib:test_httplib_https_request')
    def _test():
        connection = httplib.HTTPSConnection('localhost', server.port)
        # It doesn't matter that a SSL exception is raised here because the
        # agent still records this as an external request
        try:
            connection.request('GET', '/')
        except Exception:
            pass
        connection.close()

    _test()


def test_httplib_http_with_port_request(server):

    scoped = [select_python_version(
            py2=('External/localhost:%d/httplib/' % server.port, 1),
            py3=('External/localhost:%d/http/' % server.port, 1))]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            select_python_version(py2=('External/localhost:%d/httplib/' % server.port, 1),
                                py3=('External/localhost:%d/http/' % server.port, 1))]

    @validate_transaction_metrics(
            'test_httplib:test_httplib_http_with_port_request',
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @background_task(name='test_httplib:test_httplib_http_with_port_request')
    def _test():
        connection = httplib.HTTPConnection('localhost', server.port)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    _test()


@pytest.mark.parametrize('distributed_tracing,span_events', (
    (True, True),
    (True, False),
    (False, False),
))
def test_httplib_cross_process_request(server, distributed_tracing, span_events):
    @background_task(name='test_httplib:test_httplib_cross_process_request')
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        connection = httplib.HTTPConnection('localhost', server.port)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    _test = override_application_settings({
        'distributed_tracing.enabled': distributed_tracing,
        'span_events.enabled': span_events,
    })(_test)

    _test()


_test_httplib_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@insert_incoming_headers
def test_httplib_cross_process_response(server):
    scoped = [
            ('ExternalTransaction/localhost:%d/1#2/test' % server.port, 1)]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            ('ExternalApp/localhost:%d/1#2/all' % server.port, 1),
            ('ExternalTransaction/localhost:%d/1#2/test' % server.port, 1)]

    @validate_transaction_metrics(
            'test_httplib:test_httplib_cross_process_response',
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @validate_external_node_params(
            params=_test_httplib_cross_process_response_external_node_params)
    @background_task(name='test_httplib:test_httplib_cross_process_response')
    def _test():
        connection = httplib.HTTPConnection('localhost', server.port)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    _test()


def test_httplib_multiple_requests_cross_process_response(server):
    connection = httplib.HTTPConnection('localhost', server.port)

    scoped = [
            ('ExternalTransaction/localhost:%d/1#2/test' % server.port, 1)]

    rollup = [
            ('External/all', 1),
            ('External/allOther', 1),
            ('External/localhost:%d/all' % server.port, 1),
            ('ExternalApp/localhost:%d/1#2/all' % server.port, 1),
            ('ExternalTransaction/localhost:%d/1#2/test' % server.port, 1)]

    @validate_transaction_metrics(
            'test_httplib:test_transaction',
            scoped_metrics=scoped,
            rollup_metrics=rollup,
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


def process_response(response):
    response = response.decode('utf-8').strip()
    values = response.splitlines()
    values = [[x.strip() for x in s.split(':', 1)] for s in values]
    return {v[0]: v[1] for v in values}


def test_httplib_multiple_requests_unique_distributed_tracing_id(server):
    connection = httplib.HTTPConnection('localhost', server.port)
    response_headers = []

    @background_task(name='test_httplib:test_transaction')
    def test_transaction():
        connection.request('GET', '/')
        response = connection.getresponse()
        response_headers.append(process_response(response.read()))
        connection.request('GET', '/')
        response = connection.getresponse()
        response_headers.append(process_response(response.read()))

    test_transaction = override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    })(test_transaction)
    # make multiple requests with the same connection
    test_transaction()

    connection.close()
    dt_payloads = [DistributedTracePayload.from_http_safe(header['newrelic'])
        for header in response_headers]

    ids = set()
    for payload in dt_payloads:
        assert payload['d']['id'] not in ids
        ids.add(payload['d']['id'])


def test_httplib_nr_headers_added(server):
    connection = httplib.HTTPConnection('localhost', server.port)
    key = 'newrelic'
    value = 'testval'
    headers = []

    @background_task(name='test_httplib:test_transaction')
    def test_transaction():
        connection.putrequest('GET', '/')
        connection.putheader(key, value)
        connection.endheaders()
        response = connection.getresponse()
        headers.append(process_response(response.read()))

    test_transaction = override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    })(test_transaction)
    test_transaction()
    connection.close()
    # verify newrelic headers already added do not get overrode
    assert headers[0][key] == value


def test_span_events(server):
    connection = httplib.HTTPConnection('localhost', server.port)

    _settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    uri = 'http://localhost:%d' % server.port

    exact_intrinsics = {
        'name': select_python_version(
                py2='External/localhost:%d/httplib/' % server.port,
                py3='External/localhost:%d/http/' % server.port),
        'type': 'Span',
        'sampled': True,

        'category': 'http',
        'span.kind': 'client',
        'component': select_python_version(py2='httplib', py3='http')
    }
    exact_agents = {
        'http.url': uri,
        'http.statusCode': 200,
    }

    expected_intrinsics = ('timestamp', 'duration', 'transactionId')

    @override_application_settings(_settings)
    @validate_span_events(
            count=1,
            exact_intrinsics=exact_intrinsics,
            exact_agents=exact_agents,
            expected_intrinsics=expected_intrinsics)
    @validate_tt_segment_params(exact_params=exact_agents)
    @background_task(name='test_httplib:test_span_events')
    def _test():
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()

    _test()
