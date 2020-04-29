import uvloop
import pytest
from newrelic.api.background_task import background_task, BackgroundTask
from newrelic.api.application import application_instance as application
from newrelic.api.time_trace import current_trace
from newrelic.api.function_trace import FunctionTrace, function_trace
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace

from newrelic.core.trace_cache import trace_cache
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings, function_not_called)


@function_trace('waiter3')
async def child():
    pass


async def waiter(asyncio, event, wait):
    with FunctionTrace(name='waiter1', terminal=True):
        event.set()

        # Block until the parent says to exit
        await wait.wait()

    with FunctionTrace(name='waiter2', terminal=True):
        pass

    await child()


async def task(asyncio, trace, event, wait):
    # Test that the trace has been propagated onto this task
    assert current_trace() is trace

    # Start a function trace, this should not interfere with context in the
    # parent task
    await waiter(asyncio, event, wait)


@background_task(name='test_context_propagation')
async def _test(asyncio, schedule, nr_enabled=True):
    trace = current_trace()

    if nr_enabled:
        assert trace is not None
    else:
        assert trace is None

    events = [asyncio.Event() for _ in range(2)]
    wait = asyncio.Event()
    tasks = [schedule(task(asyncio, trace, events[idx], wait))
            for idx in range(2)]

    await asyncio.gather(*(e.wait() for e in events))

    # Test that the current trace is still "trace" even though the tasks are
    # active
    assert current_trace() is trace

    # Unblock the execution of the tasks and wait for the tasks to terminate
    wait.set()
    await asyncio.gather(*tasks)

    return trace


@pytest.mark.parametrize('loop_policy', (None, uvloop.EventLoopPolicy()))
@pytest.mark.parametrize('schedule', (
    'create_task',
    'ensure_future',
))
@validate_transaction_metrics(
    'test_context_propagation',
    background_task=True,
    scoped_metrics=(
        ('Function/waiter1', 2),
        ('Function/waiter2', 2),
        ('Function/waiter3', 2),
    ),
)
def test_context_propagation(schedule, loop_policy):
    import asyncio
    asyncio.set_event_loop_policy(loop_policy)
    loop = asyncio.get_event_loop()

    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    loop.set_exception_handler(handle_exception)

    schedule = getattr(asyncio, schedule, None) or getattr(loop, schedule)

    # Keep the trace around so that it's not removed from the trace cache
    # through reference counting (for testing)
    _ = loop.run_until_complete(_test(asyncio, schedule))

    # The agent should have removed all traces from the cache since
    # run_until_complete has terminated (all callbacks scheduled inside the
    # task have run)
    assert not trace_cache()._cache

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


@override_generic_settings(global_settings(), {
    'enabled': False,
})
@function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
def test_nr_disabled():
    import asyncio
    schedule = asyncio.ensure_future

    loop = asyncio.get_event_loop()

    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    loop.set_exception_handler(handle_exception)

    loop.run_until_complete(_test(asyncio, schedule, nr_enabled=False))

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


@pytest.mark.parametrize('trace', [
    function_trace(name='simple_gen'),
    external_trace(library='lib', url='http://foo.com'),
    database_trace('select * from foo'),
    datastore_trace('lib', 'foo', 'bar'),
    message_trace('lib', 'op', 'typ', 'name'),
    memcache_trace('cmd'),
])
def test_two_transactions(trace):
    """
    Instantiate a coroutine in one transaction and await it in
    another. This should not cause any errors.
    """
    import asyncio
    tasks = []

    ready = asyncio.Event()
    done = asyncio.Event()

    @trace
    async def task():
        pass

    @background_task(name="create_coro")
    async def create_coro():
        for _ in range(2):
            coro = task()
            tasks.append(coro)

        ready.set()
        await done.wait()

    @background_task(name="await")
    async def await_task():
        await ready.wait()
        while len(tasks) > 0:
            task = tasks.pop()
            await task

        done.set()

    afut = asyncio.ensure_future(create_coro())
    bfut = asyncio.ensure_future(await_task())
    asyncio.get_event_loop().run_until_complete(asyncio.gather(afut, bfut))


# Sentinel left in cache transaction exited
async def sentinel_in_cache_txn_exited(bg):
    sentinel = None
    with BackgroundTask(application(), 'fg') as txn:
        sentinel = txn.root_span
        task = asyncio.ensure_future(bg())
    await asyncio.sleep(0)
    return task


# Trace left in cache, transaction exited
async def trace_in_cache_txn_exited(bg):
    trace = None
    with BackgroundTask(application(), 'fg'):
        with FunctionTrace('fg') as _trace:
            trace = _trace
            task = asyncio.ensure_future(bg())
    await asyncio.sleep(0)
    return task


# Trace left in cache, transaction active
async def trace_in_cache_txn_active(bg):
    trace = None
    with BackgroundTask(application(), 'fg'):
        with FunctionTrace('fg') as _trace:
            trace = _trace
            task = asyncio.ensure_future(bg())
        await asyncio.sleep(0)
    return task


@pytest.mark.parametrize('fg', (sentinel_in_cache_txn_exited,
                                trace_in_cache_txn_exited,
                                trace_in_cache_txn_active,))
def test_transaction_exit_trace_cache(fg):
    """
    Verifying that the use of ensure_future will not cause errors
    when traces remain in the trace cache after transaction exit
    """
    import asyncio
    trace_root = []
    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    async def bg():
        with BackgroundTask(
                application(), 'bg'):
            await asyncio.sleep(0)

    @background_task(name="fg")
    async def fg():
        sentinel = current_trace()
        trace_root.append(sentinel)
        return asyncio.ensure_future(bg())

    async def handler():
        bg = await fg()
        await bg

    def _test():
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
        return loop.run_until_complete(handler())

    _test()

    # The agent should have removed all traces from the cache since
    # run_until_complete has terminated
    assert not trace_cache()._cache

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


def test_sentinel_exited_drop_trace_exception():
    """
    This test implements a circular reference which causes an exception
    to be raised in TraceCache drop_trace(). It verifies that the
    sentinel.exited property is set to true if an exception is raised
    in drop_trace()
    """
    import asyncio
    expected_error = "not the current trace"

    @background_task(name="bg")
    async def bg():
        pass

    async def create_transaction():
        try:
            txn = None
            sentinel = None
            with BackgroundTask(application(), "Parent") as txn:
                sentinel = txn.root_span
                other_txn = asyncio.ensure_future(bg())
                with FunctionTrace("trace"):
                    txn.__exit__(None, None, None)
            await other_txn
        except RuntimeError as e:
            assert str(e) == expected_error
        finally:
            assert sentinel.exited

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_transaction())
