import functools
import pytest
import sys
import time

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics, validate_transaction_errors,
        validate_tt_parenting)
from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task
from newrelic.api.database_trace import database_trace, DatabaseTrace
from newrelic.api.datastore_trace import datastore_trace, DatastoreTrace
from newrelic.api.function_trace import function_trace, FunctionTrace
from newrelic.api.external_trace import external_trace, ExternalTrace
from newrelic.api.memcache_trace import memcache_trace, MemcacheTrace
from newrelic.api.message_trace import message_trace, MessageTrace
from newrelic.common.coroutine import TraceContext

is_pypy = hasattr(sys, 'pypy_version_info')


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


@validate_tt_parenting(
    ('TransactionNode', [
        ('FunctionNode', [
            ('FunctionNode', []),
            ('FunctionNode', []),
        ]),
    ],
))
@validate_transaction_metrics('test_coroutine_siblings',
        background_task=True,
        scoped_metrics=[('Function/child', 2)],
        rollup_metrics=[('Function/child', 2)])
@background_task(name='test_coroutine_siblings')
def test_coroutine_siblings():
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

    parent()


class MyException(Exception):
    pass


@validate_transaction_metrics('test_coroutine_error',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
@validate_transaction_errors(errors=['test_coroutine_trace:MyException'])
def test_coroutine_error():
    @function_trace(name='coro')
    def coro():
        yield

    @background_task(name='test_coroutine_error')
    def _test():
        gen = coro()
        gen.send(None)
        gen.throw(MyException)

    with pytest.raises(MyException):
        _test()


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
def test_coroutine_handles_terminal_nodes():
    # somtimes coroutines can be called underneath terminal nodes
    # In this case, the trace shouldn't actually be created and we also
    # shouldn't get any errors

    @function_trace(name='coro')
    def coro():
        yield
        time.sleep(0.1)

    @function_trace(name='parent', terminal=True)
    def parent():
        # parent calls child
        for _ in coro():
            pass

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name='test_coroutine_handles_terminal_nodes')
    def _test():
        parent()

    _test()

    metric_key = ('Function/parent', '')
    assert full_metrics[metric_key].total_exclusive_call_time >= 0.1


@validate_transaction_metrics('test_coroutine_close_ends_trace',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
@background_task(name='test_coroutine_close_ends_trace')
def test_coroutine_close_ends_trace():
    @function_trace(name='coro')
    def coro():
        yield

    gen = coro()

    # kickstart the coroutine
    next(gen)

    # trace should be ended/recorded by close
    gen.close()

    # We may call gen.close as many times as we want
    gen.close()


@validate_tt_parenting(
    ('TransactionNode', [
        ('FunctionNode', [
            ('FunctionNode', []),
        ]),
    ],
))
@validate_transaction_metrics('test_coroutine_parents',
        background_task=True,
        scoped_metrics=[('Function/child', 1), ('Function/parent', 1)],
        rollup_metrics=[('Function/child', 1), ('Function/parent', 1)])
def test_coroutine_parents():

    @function_trace(name='child')
    def child():
        yield
        time.sleep(0.1)
        yield

    @function_trace(name='parent')
    def parent():
        time.sleep(0.1)
        yield
        for _ in child():
            pass

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name='test_coroutine_parents')
    def _test():
        for _ in parent():
            pass

    _test()

    # Check that the child time is subtracted from the parent time (parenting
    # relationship is correctly established)
    key = ('Function/parent', '')
    assert full_metrics[key].total_exclusive_call_time < 0.2


@validate_transaction_metrics('test_throw_yields_a_value',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
@background_task(name='test_throw_yields_a_value')
def test_throw_yields_a_value():

    @function_trace(name='coro')
    def coro():
        for _ in range(2):
            try:
                yield
            except MyException:
                yield 'foobar'

    c = coro()

    # kickstart the coroutine
    next(c)

    assert c.throw(MyException) == 'foobar'

    # finish consumption of the coroutine if necessary
    for _ in c:
        pass


@pytest.mark.parametrize('trace', [
    function_trace(name='simple_gen'),
    external_trace(library='lib', url='http://foo.com'),
    database_trace('select * from foo'),
    datastore_trace('lib', 'foo', 'bar'),
    message_trace('lib', 'op', 'typ', 'name'),
    memcache_trace('cmd'),
])
def test_coroutine_functions_outside_of_transaction(trace):

    @trace
    def coro():
        for _ in range(2):
            yield 'foo'

    assert [_ for _ in coro()] == ['foo', 'foo']


@validate_transaction_metrics(
        'test_catching_generator_exit_causes_runtime_error',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
@background_task(name='test_catching_generator_exit_causes_runtime_error')
def test_catching_generator_exit_causes_runtime_error():

    @function_trace(name='coro')
    def coro():
        try:
            yield
        except GeneratorExit:
            yield

    gen = coro()

    # kickstart the coroutine (we're inside the try now)
    next(gen)

    # Generators cannot catch generator exit exceptions (which are injected by
    # close). This will result in a runtime error.
    with pytest.raises(RuntimeError):
        gen.close()


@validate_transaction_metrics(
        'test_coroutine_time_excludes_creation_time',
        background_task=True,
        scoped_metrics=[('Function/coro', 1)],
        rollup_metrics=[('Function/coro', 1)])
def test_coroutine_time_excludes_creation_time():

    @function_trace(name='coro')
    def coro():
        yield

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name='test_coroutine_time_excludes_creation_time')
    def _test():
        gen = coro()
        time.sleep(0.1)
        for _ in gen:
            pass

    _test()

    # check that the trace does not include the time between creation and
    # consumption
    assert full_metrics[('Function/coro', '')].total_call_time < 0.1


@validate_tt_parenting(
    ('TransactionNode', [
        ('FunctionNode', []),  # coro
        ('FunctionNode', [  # child
            ('FunctionNode', []),  # child-coro
        ]),
    ],
))
@background_task(name='test_coroutine_saves_trace')
def test_coroutine_saves_trace():
    @function_trace(name='coro')
    def coro():
        yield

    @function_trace(name='child')
    def child(_coro):
        yield
        # This should exhaust the coro and hopefully not change the current
        # node
        list(_coro)

        # If the current node has been changed, this coroutine will be childed
        # underneath a node other than "child" which is incorrect.
        for _ in coro():
            pass

    _coro = coro()
    _child = child(_coro)

    # Run the child until complete
    list(_child)


@pytest.mark.parametrize('nr_transaction', [True, False])
def test_incomplete_coroutine(nr_transaction):

    @function_trace(name='coro')
    def coro():
        for _ in range(5):
            yield

    def _test():
        c = coro()

        for _ in c:
            break

        if is_pypy:
            # pypy is not guaranteed to delete the coroutine when it goes out
            # of scope. This code "helps" pypy along. The test above is really
            # just to verify that incomplete coroutines will "eventually" be
            # cleaned up. In pypy, unfortunately that means it may not be
            # reported all the time. A customer would be expected to call gc
            # directly; however, they already have to handle this case since
            # incomplete generators are well documented as having problems with
            # pypy's gc.

            # See:
            # http://doc.pypy.org/en/latest/cpython_differences.html#differences-related-to-garbage-collection-strategies
            # https://bitbucket.org/pypy/pypy/issues/736
            del c
            import gc
            gc.collect()

    if nr_transaction:
        _test = validate_transaction_metrics(
                'test_incomplete_coroutine',
                background_task=True,
                scoped_metrics=[('Function/coro', 1)],
                rollup_metrics=[('Function/coro', 1)],
        )(background_task(name='test_incomplete_coroutine')(_test))

    _test()


if sys.version_info >= (3, 5):
    from _test_async_coroutine_trace import *  # NOQA
