import pytest
import asyncio
import time
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings)


@background_task(name="block")
@asyncio.coroutine
def block_loop(ready, done, blocking_transaction_active):
    yield from ready.wait()
    time.sleep(0.1)
    done.set()
    if blocking_transaction_active:
        ready.clear()
        yield from ready.wait()


@function_trace(name="waiter")
@asyncio.coroutine
def waiter(ready, done):
    ready.set()
    yield from done.wait()


@background_task(name="wait")
@asyncio.coroutine
def wait_for_loop(ready, done):
    # Run the waiter on another task so that the sentinel for wait appears
    # multiple times in the trace cache
    yield from asyncio.ensure_future(waiter(ready, done))

    ready.set()


@pytest.mark.parametrize(
    'blocking_transaction_active,event_loop_visibility_enabled', (
    (True, True),
    (False, True),
    (False, False),
))
def test_record_event_loop_wait(
        blocking_transaction_active,
        event_loop_visibility_enabled):
    import asyncio

    metric_count = 1 if event_loop_visibility_enabled else None

    scoped = (
        ("EventLoop/Wait/OtherTransaction/Function/block", metric_count),
    )
    rollup = (
        ("EventLoop/Wait/all", metric_count),
        ("EventLoop/Wait/allOther", metric_count),
    )

    ready, done = (asyncio.Event(), asyncio.Event())
    future = asyncio.gather(
        wait_for_loop(ready, done),
        block_loop(ready, done, blocking_transaction_active),
    )

    index = 0 if blocking_transaction_active else -1

    @override_application_settings({
        'event_loop_visibility.enabled': event_loop_visibility_enabled,
    })
    @validate_transaction_metrics(
        "wait",
        scoped_metrics=scoped,
        rollup_metrics=rollup,
        background_task=True,
        index=index,
    )
    def _test():
        asyncio.get_event_loop().run_until_complete(future)

    _test()
