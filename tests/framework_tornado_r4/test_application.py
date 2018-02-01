import multiprocessing
import pytest
import socket
import sys
import tornado

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics, override_generic_settings,
        validate_transaction_errors, override_ignore_status_codes,
        validate_transaction_event_attributes, function_not_called,
        override_application_settings, validate_transaction_trace_attributes,
        validate_attributes)
from newrelic.core.config import global_settings
from tornado.ioloop import IOLoop

from remove_utilization_tester import remove_utilization_tester


VERSION = '.'.join(map(str, tornado.version_info))

if IOLoop.configurable_default().__name__ == 'AsyncIOLoop':
    # This is Python 3 and Tornado v5, only the default is allowable
    loops = [None]
elif sys.version_info < (3, 4):
    loops = [None, 'zmq.eventloop.ioloop.ZMQIOLoop']
else:
    loops = [None, 'tornado.platform.asyncio.AsyncIOLoop',
            'zmq.eventloop.ioloop.ZMQIOLoop']


_tests = [
    ('/simple', '_target_application:SimpleHandler.get'),
    ('/coro', '_target_application:CoroHandler.get'),
    ('/fake-coro', '_target_application:FakeCoroHandler.get'),
    ('/coro-throw', '_target_application:CoroThrowHandler.get'),
    ('/web-async', '_target_application:WebAsyncHandler.get'),
    ('/init', '_target_application:InitializeHandler.get'),
    ('/on-finish', '_target_application:OnFinishHandler.get'),
]
if sys.version_info >= (3, 5) and tornado.version_info >= (4, 3):
    _tests.extend([
        ('/native-simple',
                '_target_application_native:NativeSimpleHandler.get'),
        ('/native-web-async',
                '_target_application_native:NativeWebAsyncHandler.get'),
    ])


@pytest.mark.xfail(tornado.version_info < (4, 5), strict=True,
        reason='PYTHON-2629')
@pytest.mark.parametrize('uri,name', _tests)
@pytest.mark.parametrize('ioloop', loops)
def test_simple(app, uri, name, ioloop):

    metric_list = []
    full_metrics = {}
    metric_name = 'Function/%s' % name
    framework_metric_name = 'Python/Framework/Tornado/ASYNC/%s' % VERSION
    txn_metric_name = 'WebTransaction/%s' % metric_name

    @validate_transaction_metrics(name,
        rollup_metrics=[(metric_name, 1)],
        scoped_metrics=[(metric_name, 1)],
        custom_metrics=[(framework_metric_name, 1)],
    )
    @validate_transaction_errors(errors=[])
    @capture_transaction_metrics(metric_list, full_metrics)
    @validate_transaction_event_attributes(
        required_params={
            'agent': ['response.headers.contentType'],
            'user': [], 'intrinsic': [],
        },
        forgone_params={
            'agent': [], 'user': [], 'intrinsic': [],
        },
        exact_attrs={
            'agent': {
                'request.method': 'GET',
                'response.status': '200',
            },
            'user': {},
            'intrinsic': {'port': app.get_http_port()},
        },
    )
    def _test():
        response = app.fetch(uri)
        assert response.code == 200

        # validate time reported is at least 0.1 seconds
        unscoped_metric = (txn_metric_name, '')
        assert unscoped_metric in full_metrics, full_metrics
        assert full_metrics[unscoped_metric][1] >= 0.1
        assert full_metrics[unscoped_metric][1] < 0.2

    _test()


@pytest.mark.xfail(tornado.version_info < (4, 5), strict=True,
        reason='PYTHON-2629')
@pytest.mark.parametrize('method', [
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH'
])
@pytest.mark.parametrize('request_param_setting', [
    'attributes.include',
    'attributes.exclude'
])
@pytest.mark.parametrize('sock_family', [
    socket.AF_INET,
    socket.AF_INET6,
])
def test_environ(app, method, request_param_setting, sock_family):

    # Ensure that passing a port in the headers
    # does not affect what New Relic records.
    # This was an issue with r3 instrumentation.
    headers = {'Host': 'localhost:1234'}

    uri = '/simple/fast?foo=bar'
    name = '_target_application:SimpleHandler.get'

    metric_name = 'Function/%s' % name
    framework_metric_name = 'Python/Framework/Tornado/ASYNC/%s' % VERSION

    agent_exact_attrs = {'request.method': method, 'response.status': '200'}
    if request_param_setting == 'attributes.include':
        agent_exact_attrs['request.parameters.foo'] = 'bar'

    @override_application_settings(
            {request_param_setting: ['request.parameters.*']})
    @validate_transaction_metrics(name,
        rollup_metrics=[(metric_name, 1)],
        scoped_metrics=[(metric_name, 1)],
        custom_metrics=[(framework_metric_name, 1)],
    )
    @validate_transaction_event_attributes(
        required_params={
            'agent': ['response.headers.contentType'],
            'user': [], 'intrinsic': [],
        },
        exact_attrs={
            'agent': agent_exact_attrs,
            'user': {},
            'intrinsic': {'port': app.get_http_port()},
        },
    )
    @validate_transaction_trace_attributes(url='/simple/fast')
    def _test():

        if method in ('GET', 'DELETE'):
            response = app.fetch(uri, method=method, headers=headers)
        else:
            response = app.fetch(uri, body=b'', method=method,
                    headers=headers)

        assert response.code == 200

    _test()


@pytest.mark.parametrize('ioloop', loops)
def test_websocket(app, ioloop):
    headers = {'Upgrade': 'websocket'}

    @function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _test():
        response = app.fetch('/simple/fast', headers=headers)
        assert response.code == 200

    _test()


@pytest.mark.parametrize('ioloop', loops)
@pytest.mark.parametrize('nr_enabled,ignore_status_codes', [
    (True, []),
    (True, [405]),
    (False, None),
])
def test_unsupported_method(app, ioloop, nr_enabled, ignore_status_codes):

    def _test():
        response = app.fetch('/simple',
                method='TEAPOT', body=b'', allow_nonstandard_methods=True)
        assert response.code == 405

    if nr_enabled:
        _test = override_ignore_status_codes(ignore_status_codes)(_test)
        _test = validate_transaction_metrics(
                '_target_application:SimpleHandler')(_test)

        if ignore_status_codes:
            _test = validate_transaction_errors(errors=[])(_test)
        else:
            _test = validate_transaction_errors(
                    errors=['tornado.web:HTTPError'])(_test)
    else:
        settings = global_settings()
        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()


@pytest.mark.parametrize('ioloop', loops)
def test_nr_disabled(app, ioloop):

    settings = global_settings()

    @override_generic_settings(settings, {'enabled': False})
    def _test():
        response = app.fetch('/simple/fast')
        assert response.code == 200

    _test()


@pytest.mark.xfail(reason='Auto-RUM not implemented', strict=True)
@pytest.mark.parametrize('ioloop', loops)
def test_html_insertion(app, ioloop):

    settings = global_settings()
    _test_html_insertion_settings = {
        'browser_monitoring.enabled': True,
        'browser_monitoring.auto_instrument': True,
        'js_agent_loader': u'<!-- NREUM HEADER -->',
    }

    @override_generic_settings(settings, _test_html_insertion_settings)
    @validate_transaction_metrics(
            '_target_application:HTMLInsertionHandler.get')
    @validate_transaction_errors(errors=[])
    def _test():
        response = app.fetch('/html-insertion')
        assert response.code == 200
        assert b'Hello World!' in response.body

        # The 'NREUM HEADER' value comes from our override for the header.
        # The 'NREUM.info' value comes from the programmatically generated
        # footer added by the agent.

        assert b'NREUM HEADER' in response.body
        assert b'NREUM.info' in response.body

    _test()


@pytest.mark.parametrize('now', [True, False])
def test_thread_utilization_disabled(now):
    # What we want to test here is code that is executed during agent
    # initialization/registration. Thus we launch the agent in a new process so
    # that we can run the import-initialization-registration process manually
    # and make assertions against it.

    q = multiprocessing.Queue()
    process = multiprocessing.Process(target=remove_utilization_tester,
            kwargs={'now': now, 'queue': q})
    process.start()
    result = q.get(timeout=15)

    assert result == 'PASS'


@pytest.mark.parametrize('header_key,agent_attr', [
    ('Content-Type', 'request.headers.contentType'),
    ('Referer', 'request.headers.referer'),
    ('User-Agent', 'request.headers.userAgent'),
])
@pytest.mark.parametrize('ioloop', loops)
def test_request_headers(app, ioloop, header_key, agent_attr):

    required_attr_names = ['request.headers.host', 'request.method',
            agent_attr]

    @validate_transaction_metrics('_target_application:SimpleHandler.get')
    @validate_transaction_errors(errors=[])
    @validate_attributes('agent', required_attr_names=required_attr_names)
    def _test():
        response = app.fetch('/simple/fast', headers={header_key: 'tacocat'})
        assert response.code == 200

    _test()
