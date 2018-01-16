import pytest
import six
import sys
import tornado

from tornado.ioloop import IOLoop

from testing_support.fixtures import (validate_synthetics_event,
        override_application_settings, make_synthetics_header,
        validate_transaction_metrics)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)


ENCODING_KEY = '1234567890123456789012345678901234567890'
ACCOUNT_ID = '444'
SYNTHETICS_RESOURCE_ID = '09845779-16ef-4fa7-b7f2-44da8e62931c'
SYNTHETICS_JOB_ID = '8c7dd3ba-4933-4cbb-b1ed-b62f511782f4'
SYNTHETICS_MONITOR_ID = 'dc452ae9-1a93-4ab5-8a33-600521e9cd00'

_override_settings = {
    'encoding_key': ENCODING_KEY,
    'trusted_account_ids': [int(ACCOUNT_ID)],
    'synthetics.enabled': True,
}

if IOLoop.configurable_default().__name__ == 'AsyncIOLoop':
    # This is Python 3 and Tornado v5, only the default is allowable
    loops = [None]
elif sys.version_info < (3, 4):
    loops = [None, 'zmq.eventloop.ioloop.ZMQIOLoop']
else:
    loops = [None, 'tornado.platform.asyncio.AsyncIOLoop',
            'zmq.eventloop.ioloop.ZMQIOLoop']


skipif_tornadomaster_py3 = pytest.mark.skipif(
        tornado.version_info >= (5, 0) and six.PY3,
        reason=('Instrumentation is broken for Tornado 5.0. Running these '
            'tests results in a hang.'))


@pytest.fixture(scope='module')
def external():
    external = MockExternalHTTPHResponseHeadersServer()
    with external:
        yield external


def _make_synthetics_header(version='1', account_id=ACCOUNT_ID,
        resource_id=SYNTHETICS_RESOURCE_ID, job_id=SYNTHETICS_JOB_ID,
        monitor_id=SYNTHETICS_MONITOR_ID, encoding_key=ENCODING_KEY):
    return make_synthetics_header(account_id, resource_id, job_id,
            monitor_id, encoding_key, version)


_test_valid_synthetics_event_required = [
        ('nr.syntheticsResourceId', SYNTHETICS_RESOURCE_ID),
        ('nr.syntheticsJobId', SYNTHETICS_JOB_ID),
        ('nr.syntheticsMonitorId', SYNTHETICS_MONITOR_ID)]
_test_valid_synthetics_event_forgone = []


@pytest.mark.parametrize('ioloop', loops)
@override_application_settings(_override_settings)
def test_valid_synthetics_event(app, ioloop):

    @validate_synthetics_event(_test_valid_synthetics_event_required,
            _test_valid_synthetics_event_forgone, should_exist=True)
    def _test():
        headers = _make_synthetics_header()
        response = app.fetch('/simple/fast', headers=headers)
        assert response.code == 200

    _test()


@skipif_tornadomaster_py3
@pytest.mark.parametrize('client_class',
        ['AsyncHTTPClient', 'CurlAsyncHTTPClient', 'HTTPClient'])
@pytest.mark.parametrize('cat_enabled', [True, False])
@pytest.mark.parametrize('synthetics_enabled', [True, False])
@pytest.mark.parametrize('request_type', ['uri', 'class'])
@override_application_settings(_override_settings)
def test_synthetics_headers_sent_on_external_requests(app, cat_enabled,
        synthetics_enabled, request_type, client_class, external):

    if cat_enabled or ('Async' not in client_class):
        port = external.port
    else:
        port = app.get_http_port()

    uri = '/async-client/%s/%s/%s' % (port, request_type, client_class)

    expected_metrics = [
        ('External/localhost:%s/tornado.httpclient/GET' % port, 1)
    ]

    @override_application_settings({
        'cross_application_tracer.enabled': cat_enabled,
        'synthetics.enabled': synthetics_enabled})
    @validate_transaction_metrics(
        '_target_application:AsyncExternalHandler.get',
        rollup_metrics=expected_metrics,
        scoped_metrics=expected_metrics)
    def _test():
        synthetics_headers = _make_synthetics_header()
        response = app.fetch(uri, headers=synthetics_headers)
        assert response.code == 200

        sent_headers = response.body
        if hasattr(sent_headers, 'decode'):
            sent_headers = sent_headers.decode('utf-8')

        sent_headers_lower = sent_headers.lower()

        if cat_enabled:
            assert 'X-NewRelic-ID' in sent_headers
            assert 'X-NewRelic-Transaction' in sent_headers
            assert 'X-NewRelic-App-Data' not in sent_headers
        else:
            assert 'x-newrelic-id' not in sent_headers_lower
            assert 'x-newrelic-transaction' not in sent_headers_lower
            assert 'x-newrelic-app-data' not in sent_headers_lower

        if synthetics_enabled:
            assert 'X-NewRelic-Synthetics' in sent_headers
        else:
            assert 'x-newrelic-synthetics' not in sent_headers_lower

    _test()
