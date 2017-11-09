import multiprocessing
import pytest
import sys
import tornado

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics, override_generic_settings,
        validate_transaction_errors)
from newrelic.core.config import global_settings
from tornado.ioloop import IOLoop

from remove_utilization_tester import remove_utilization_tester


VERSION = '.'.join(map(str, tornado.version_info))

if (sys.version_info < (3, 4) or
        IOLoop.configurable_default().__name__ == 'AsyncIOLoop'):
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
if sys.version_info >= (3, 5):
    _tests.extend([
        ('/native-simple',
                '_target_application_native:NativeSimpleHandler.get'),
        ('/native-web-async',
                '_target_application_native:NativeWebAsyncHandler.get'),
    ])


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
    def _test():
        response = app.fetch(uri)
        assert response.code == 200

        # validate time reported is at least 0.1 seconds
        unscoped_metric = (txn_metric_name, '')
        assert unscoped_metric in full_metrics, full_metrics
        assert full_metrics[unscoped_metric][1] >= 0.1
        assert full_metrics[unscoped_metric][1] < 0.2

    _test()


@pytest.mark.parametrize('ioloop', loops)
def test_unsupported_method(app, ioloop):

    @validate_transaction_metrics('_target_application:SimpleHandler')
    @validate_transaction_errors(errors=['tornado.web:HTTPError'])
    def _test():
        response = app.fetch('/simple',
                method='TEAPOT', body=b'', allow_nonstandard_methods=True)
        assert response.code == 405

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
