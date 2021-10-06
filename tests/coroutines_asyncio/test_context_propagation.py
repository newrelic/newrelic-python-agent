# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

import pytest
import uvloop
from testing_support.fixtures import (
    function_not_called,
    override_generic_settings,
    validate_transaction_metrics,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import BackgroundTask, background_task
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.function_trace import FunctionTrace, function_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace
from newrelic.api.time_trace import current_trace
from newrelic.core.config import global_settings
from newrelic.core.trace_cache import trace_cache


@function_trace("waiter3")
async def child():
    pass


async def waiter(asyncio, event, wait):
    with FunctionTrace(name="waiter1", terminal=True):
        event.set()

        # Block until the parent says to exit
        await wait.wait()

    with FunctionTrace(name="waiter2", terminal=True):
        pass

    await child()


async def task(asyncio, trace, event, wait):
    # Test that the trace has been propagated onto this task
    assert current_trace() is trace

    # Start a function trace, this should not interfere with context in the
    # parent task
    await waiter(asyncio, event, wait)


@background_task(name="test_context_propagation")
async def _test(asyncio, schedule, nr_enabled=True):
    trace = current_trace()

    if nr_enabled:
        assert trace is not None
    else:
        assert trace is None

    events = [asyncio.Event() for _ in range(2)]
    wait = asyncio.Event()
    tasks = [schedule(task(asyncio, trace, events[idx], wait)) for idx in range(2)]

    await asyncio.gather(*(e.wait() for e in events))

    # Test that the current trace is still "trace" even though the tasks are
    # active
    assert current_trace() is trace

    # Unblock the execution of the tasks and wait for the tasks to terminate
    wait.set()
    await asyncio.gather(*tasks)

    return trace


@pytest.mark.parametrize("loop_policy", (None, uvloop.EventLoopPolicy()))
@pytest.mark.parametrize(
    "schedule",
    (
        "create_task",
        "ensure_future",
    ),
)
@validate_transaction_metrics(
    "test_context_propagation",
    background_task=True,
    scoped_metrics=(
        ("Function/waiter1", 2),
        ("Function/waiter2", 2),
        ("Function/waiter3", 2),
    ),
)
def test_context_propagation(event_loop, schedule, loop_policy):
    import asyncio

    asyncio.set_event_loop_policy(loop_policy)
    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    event_loop.set_exception_handler(handle_exception)

    schedule = getattr(asyncio, schedule, None) or getattr(event_loop, schedule)

    # Keep the trace around so that it's not removed from the trace cache
    # through reference counting (for testing)
    _ = event_loop.run_until_complete(_test(asyncio, schedule))

    # The agent should have removed all traces from the cache since
    # run_until_complete has terminated (all callbacks scheduled inside the
    # task have run)
    assert not trace_cache()._cache

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


@override_generic_settings(
    global_settings(),
    {
        "enabled": False,
    },
)
@function_not_called("newrelic.core.stats_engine", "StatsEngine.record_transaction")
def test_nr_disabled(event_loop):
    import asyncio

    schedule = asyncio.ensure_future

    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    event_loop.set_exception_handler(handle_exception)

    event_loop.run_until_complete(_test(asyncio, schedule, nr_enabled=False))

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


@pytest.mark.parametrize(
    "trace",
    [
        function_trace(name="simple_gen"),
        external_trace(library="lib", url="http://foo.com"),
        database_trace("select * from foo"),
        datastore_trace("lib", "foo", "bar"),
        message_trace("lib", "op", "typ", "name"),
        memcache_trace("cmd"),
    ],
)
def test_two_transactions(event_loop, trace):
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

    if sys.version_info >= (3, 10, 0):
        afut = asyncio.ensure_future(create_coro(), loop=event_loop)
        bfut = asyncio.ensure_future(await_task(), loop=event_loop)
        event_loop.run_until_complete(asyncio.gather(afut, bfut))
    else:
        afut = asyncio.ensure_future(create_coro())
        bfut = asyncio.ensure_future(await_task())
        asyncio.get_event_loop().run_until_complete(asyncio.gather(afut, bfut))


# Sentinel left in cache transaction exited
async def sentinel_in_cache_txn_exited(asyncio, bg):
    event = asyncio.Event()

    with BackgroundTask(application(), "fg") as txn:
        _ = txn.root_span
        task = asyncio.ensure_future(bg(event))

    await event.wait()
    return task


# Trace left in cache, transaction exited
async def trace_in_cache_txn_exited(asyncio, bg):
    event = asyncio.Event()

    with BackgroundTask(application(), "fg"):
        with FunctionTrace("fg") as _:
            task = asyncio.ensure_future(bg(event))

    await event.wait()
    return task


# Trace left in cache, transaction active
async def trace_in_cache_txn_active(asyncio, bg):
    event = asyncio.Event()

    with BackgroundTask(application(), "fg"):
        with FunctionTrace("fg") as _:
            task = asyncio.ensure_future(bg(event))
        await event.wait()

    return task


@pytest.mark.parametrize(
    "fg",
    (
        sentinel_in_cache_txn_exited,
        trace_in_cache_txn_exited,
        trace_in_cache_txn_active,
    ),
)
def test_transaction_exit_trace_cache(event_loop, fg):
    """
    Verifying that the use of ensure_future will not cause errors
    when traces remain in the trace cache after transaction exit
    """
    import asyncio

    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    async def bg(event):
        with BackgroundTask(application(), "bg"):
            event.set()

    async def handler():
        task = await fg(asyncio, bg)
        await task

    def _test():
        event_loop.set_exception_handler(handle_exception)
        return event_loop.run_until_complete(handler())

    _test()

    # The agent should have removed all traces from the cache since
    # run_until_complete has terminated
    assert not trace_cache()._cache

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


def test_incomplete_traces_exit_when_root_exits(event_loop):
    """Verifies that child traces in the same task are exited when the root
    exits"""

    import asyncio

    @function_trace(name="child")
    async def child(start, end):
        start.set()
        await end.wait()

    @background_task(name="parent")
    async def parent():
        start = asyncio.Event()
        end = asyncio.Event()
        task = asyncio.ensure_future(child(start, end))
        await start.wait()
        end.set()
        return task

    @validate_transaction_metrics(
        "parent",
        background_task=True,
        scoped_metrics=[("Function/child", 1)],
    )
    def test(loop):
        return loop.run_until_complete(parent())

    task = test(event_loop)
    event_loop.run_until_complete(task)


def test_incomplete_traces_with_multiple_transactions(event_loop):
    import asyncio

    @background_task(name="dummy")
    async def dummy():
        task = asyncio.ensure_future(child(True))
        await end.wait()
        await task

    @function_trace(name="child")
    async def child(running_at_end=False):
        trace = current_trace()
        start.set()
        await end.wait()
        if running_at_end:
            assert current_trace() is trace
        else:
            assert current_trace() is not trace

    @background_task(name="parent")
    async def parent():
        task = asyncio.ensure_future(child())
        await start.wait()
        return task

    @validate_transaction_metrics(
        "parent",
        background_task=True,
        scoped_metrics=[("Function/child", 1)],
    )
    def parent_assertions(task):
        return event_loop.run_until_complete(task)

    @validate_transaction_metrics(
        "dummy",
        background_task=True,
        scoped_metrics=[("Function/child", 1)],
    )
    def dummy_assertions(task):
        return event_loop.run_until_complete(task)

    async def startup():
        return asyncio.Event(), asyncio.Event()

    async def start_dummy():
        dummy_task = asyncio.ensure_future(dummy())
        await start.wait()
        start.clear()
        return dummy_task

    start, end = event_loop.run_until_complete(startup())

    # Kick start dummy transaction (forcing an ensure_future on another
    # transaction)
    dummy_task = event_loop.run_until_complete(start_dummy())

    # start and end a transaction, forcing the child to truncate
    child_task = parent_assertions(parent())

    # Signal to end any in progress tasks
    # * dummy
    # * dummy->child
    # * parent[ended]->child
    end.set()

    # Wait for dummy/parent->child to terminate
    dummy_assertions(dummy_task)
    event_loop.run_until_complete(child_task)


@validate_transaction_metrics("Parent", background_task=True)
def test_transaction_end_on_different_task(event_loop):
    import asyncio

    txn = BackgroundTask(application(), name="Parent")

    async def parent():
        txn.__enter__()
        child_start = asyncio.Event()
        parent_end = asyncio.Event()
        child_task = asyncio.ensure_future(child(child_start, parent_end))
        await child_start.wait()
        parent_end.set()
        return child_task

    async def child(child_start, parent_end):
        child_start.set()
        await parent_end.wait()

        # Calling asyncio.sleep(0) allows the scheduled done callbacks to run
        # done callbacks are scheduled through call_soon
        await asyncio.sleep(0)
        txn.__exit__(None, None, None)

    async def test():
        task = await asyncio.ensure_future(parent())
        await task

    event_loop.run_until_complete(test())
