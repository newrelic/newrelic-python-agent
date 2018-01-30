import functools
import pytest
import time

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics, validate_transaction_errors)
from newrelic.api.background_task import background_task
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.function_trace import function_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace


@pytest.mark.parametrize('trace,metric', [
    (functools.partial(function_trace, name='simple_gen'),
            'Function/simple_gen'),
    (functools.partial(external_trace, library='lib', url='http://foo.com'),
            'External/foo.com/lib/'),
    (functools.partial(database_trace, 'select * from foo'),
            'Datastore/statement/None/foo/select'),
    (functools.partial(datastore_trace, 'lib', 'foo', 'bar'),
            'Datastore/statement/lib/foo/bar'),
    (functools.partial(message_trace, 'lib', 'op', 'typ', 'name'),
            'MessageBroker/lib/typ/op/Named/name'),
    (functools.partial(memcache_trace, 'cmd'),
            'Memcache/cmd'),
])
def test_coroutine_timing(trace, metric):
    @trace()
    def simple_gen():
        time.sleep(0.1)
        yield
        time.sleep(0.1)

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
        for _ in simple_gen():
            pass

    _test()

    # Check that coroutines time the total call time (including pauses)
    metric_key = (metric, '')
    assert full_metrics[metric_key].total_call_time >= 0.2


def test_coroutine_parenting():
    # The expected segment map looks like this
    # parent
    # | child
    # | child

    # Prior to adding coroutine trace, child would be a child of child
    # This test checks for the presence of 2 child metrics (which wouldn't be
    # the case if child was a child of child since child is terminal)

    @function_trace('child', terminal=True)
    def child():
        yield

    @function_trace('parent')
    def parent():
        coros = [child()]

        # start one of the children before the other
        next(coros[-1])

        coros.insert(0, child())

        while coros:
            coro = coros.pop(0)
            try:
                next(coro)
            except StopIteration:
                pass
            else:
                coros.append(coro)

    @validate_transaction_metrics('test_coroutine_parenting',
            background_task=True,
            scoped_metrics=[('Function/child', 2)],
            rollup_metrics=[('Function/child', 2)])
    @background_task(name='test_coroutine_parenting')
    def _test():
        parent()

    _test()


@validate_transaction_metrics('test_coroutine_error',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
@validate_transaction_errors(errors=['builtins:ValueError'])
def test_coroutine_error():
    @function_trace(name='coro')
    def coro():
        yield

    @background_task(name='test_coroutine_error')
    def _test():
        gen = coro()
        gen.throw(ValueError)

    try:
        _test()
    except ValueError:
        pass


@validate_transaction_metrics('test_coroutine_caught_exception',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
@validate_transaction_errors(errors=[])
def test_coroutine_caught_exception():
    @function_trace(name='coro')
    def coro():
        for _ in range(2):
            time.sleep(0.1)
            try:
                yield
            except ValueError:
                pass

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name='test_coroutine_caught_exception')
    def _test():
        gen = coro()
        # kickstart the generator (the try/except logic is inside the
        # generator)
        next(gen)
        gen.throw(ValueError)

        # consume the generator
        for _ in gen:
            pass

    # The ValueError should not be reraised
    _test()

    assert full_metrics[('Function/coro', '')].total_call_time >= 0.2


@validate_transaction_metrics('test_coroutine_handles_terminal_nodes',
        background_task=True,
        scoped_metrics=[('Function/parent', 1), ('Function/coro', None)],
        rollup_metrics=[('Function/parent', 1), ('Function/coro', None)])
@background_task(name='test_coroutine_handles_terminal_nodes')
def test_coroutine_handles_terminal_nodes():
    # somtimes coroutines can be called underneath terminal nodes
    # In this case, the trace shouldn't actually be created and we also
    # shouldn't get any errors

    @function_trace(name='coro')
    def coro():
        yield

    @function_trace(name='parent', terminal=True)
    def parent():
        # parent calls child
        for _ in coro():
            pass

    parent()
