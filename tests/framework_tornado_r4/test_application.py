import sys
import pytest
import tornado

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics, override_generic_settings)
from newrelic.core.config import global_settings
from tornado.ioloop import IOLoop


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
    @capture_transaction_metrics(metric_list, full_metrics)
    def _test():
        response = app.fetch(uri)
        assert response.code == 200

        # validate time reported is at least 0.1 seconds
        unscoped_metric = (txn_metric_name, '')
        assert unscoped_metric in full_metrics, full_metrics
        assert full_metrics[unscoped_metric][1] >= 0.1

    _test()


@pytest.mark.parametrize('ioloop', loops)
def test_unsupported_method(app, ioloop):

    @validate_transaction_metrics('_target_application:SimpleHandler')
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
