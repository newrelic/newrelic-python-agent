import pytest
from newrelic.api.background_task import background_task
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
def test_context_propagation(schedule):
    import asyncio
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
