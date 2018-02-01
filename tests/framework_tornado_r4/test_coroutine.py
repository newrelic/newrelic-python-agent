import pytest
import time

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics)
from newrelic.api.background_task import background_task
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.function_trace import function_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace


def test_coroutine_has_tornado_attrs():
    import tornado.gen

    def _kittens():
        pass

    kittens = tornado.gen.coroutine(_kittens)

    assert kittens.__wrapped__ is _kittens
    assert kittens.__tornado_coroutine__ is True


@pytest.mark.parametrize('trace,metric', [
    (function_trace(name='simple_gen'),
            'Function/simple_gen'),
    (external_trace(library='lib', url='http://foo.com'),
            'External/foo.com/lib/'),
    (database_trace('select * from foo'),
            'Datastore/statement/None/foo/select'),
    (datastore_trace('lib', 'foo', 'bar'),
            'Datastore/statement/lib/foo/bar'),
    (message_trace('lib', 'op', 'typ', 'name'),
            'MessageBroker/lib/typ/op/Named/name'),
    (memcache_trace('cmd'),
            'Memcache/cmd'),
])
@pytest.mark.parametrize('coro_decorator_first', [True, False])
def test_coroutine_timing(trace, metric, coro_decorator_first):
    import tornado.gen

    def simple_gen():
        yield tornado.gen.sleep(0)
        time.sleep(0.1)

    if coro_decorator_first:
        simple_gen = trace(tornado.gen.coroutine(simple_gen))
    else:
        simple_gen = tornado.gen.coroutine(trace(simple_gen))

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics(
            'test_coroutine_timing',
            background_task=True,
            scoped_metrics=[(metric, 1)],
            rollup_metrics=[(metric, 1)])
    @background_task(name='test_coroutine_timing')
    def _test():
        io_loop = tornado.ioloop.IOLoop.current()
        io_loop.run_sync(simple_gen)

    _test()

    # Check that coroutines time the total call time (including pauses)
    if not coro_decorator_first:
        metric_key = (metric, '')
        assert full_metrics[metric_key].total_call_time >= 0.1
