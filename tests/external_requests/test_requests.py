import pytest
import requests
import requests.exceptions

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, validate_tt_parenting,
    override_application_settings)
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)
from testing_support.mock_external_http_server import MockExternalHTTPServer

from newrelic.api.background_task import background_task


def get_requests_version():
    return tuple(map(int, requests.__version__.split('.')[:2]))


_test_requests_http_request_scoped_metrics = [
        ('External/www.example.com/requests/', 1)]

_test_requests_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('External/www.example.com/requests/', 1)]

_test_requests_http_request_get_parenting = (
    'TransactionNode', [
        ('ExternalNode', []),
    ]
)


@validate_tt_parenting(_test_requests_http_request_get_parenting)
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_http_request_get',
        scoped_metrics=_test_requests_http_request_scoped_metrics,
        rollup_metrics=_test_requests_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_get():
    requests.get('http://www.example.com/')


@pytest.mark.skipif(get_requests_version() < (0, 8),
        reason="Can't set verify=False for requests.get() in v0.7")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_https_request_get',
        scoped_metrics=_test_requests_http_request_scoped_metrics,
        rollup_metrics=_test_requests_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_https_request_get():
    requests.get('https://www.example.com/', verify=False)


_test_requests_http_request_with_port_scoped_metrics = [
        ('External/localhost:8989/requests/', 1)]

_test_requests_http_request_with_port_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        ('External/localhost:8989/requests/', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_http_request_with_port',
        scoped_metrics=_test_requests_http_request_with_port_scoped_metrics,
        rollup_metrics=_test_requests_http_request_with_port_rollup_metrics,
        background_task=True)
@background_task()
def test_http_request_with_port():
    with MockExternalHTTPServer():
        requests.get('http://localhost:8989/')


@pytest.mark.skipif(get_requests_version() < (1, 0),
        reason="Session.send() doesn't exist for requests < v1.0.")
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_http_session_send',
        scoped_metrics=_test_requests_http_request_scoped_metrics,
        rollup_metrics=_test_requests_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_http_session_send():
    session = requests.Session()
    req = requests.Request('GET', 'http://www.example.com/')
    prep_req = req.prepare()
    session.send(prep_req)


_test_requests_none_url_scoped_metrics = [
        ('External/unknown/requests/', 1)]

_test_requests_none_url_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/unknown/all', 1),
        ('External/unknown/requests/', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_none_url_get',
        scoped_metrics=_test_requests_none_url_scoped_metrics,
        rollup_metrics=_test_requests_none_url_rollup_metrics,
        background_task=True)
@background_task()
def test_none_url_get():
    try:
        requests.get(None)
    except requests.exceptions.MissingSchema:
        # Python 2.
        pass
    except TypeError:
        # Python 3.
        pass


_test_requests_wrong_datatype_url_scoped_metrics = [
        ('External/unknown.url/requests/', 1)]

_test_requests_wrong_datatype_url_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/unknown.url/all', 1),
        ('External/unknown.url/requests/', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_wrong_datatype_url_get',
        scoped_metrics=_test_requests_wrong_datatype_url_scoped_metrics,
        rollup_metrics=_test_requests_wrong_datatype_url_rollup_metrics,
        background_task=True)
@background_task()
def test_wrong_datatype_url_get():
    try:
        requests.get({'a': 1})
    except Exception:
        pass


@pytest.mark.parametrize('distributed_tracing,span_events', (
    (True, True),
    (True, False),
    (False, False),
))
def test_requests_cross_process_request(distributed_tracing, span_events):

    @validate_transaction_errors(errors=[])
    @background_task(name='test_requests:test_requests_cross_process_request')
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        requests.get('http://www.example.com/')

    flags = set()

    if distributed_tracing:
        flags.add('distributed_tracing')

    if span_events:
        flags.add('span_events')

    _test = override_application_settings(
            {'feature_flag': flags})(_test)

    _test()


_test_requests_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_requests_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        ('ExternalApp/www.example.com/1#2/all', 1),
        ('ExternalTransaction/www.example.com/1#2/test', 1)]

_test_requests_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_requests:test_requests_cross_process_response',
        scoped_metrics=_test_requests_cross_process_response_scoped_metrics,
        rollup_metrics=_test_requests_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_requests_cross_process_response_external_node_params)
@background_task()
def test_requests_cross_process_response():
    requests.get('http://www.example.com/')
