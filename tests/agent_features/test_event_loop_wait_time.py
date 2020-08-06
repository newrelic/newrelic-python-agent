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

import pytest
import asyncio
import time
from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace, FunctionTrace
from newrelic.core.trace_cache import trace_cache
from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings, validate_transaction_event_attributes,
        validate_transaction_trace_attributes)


@background_task(name="block")
@asyncio.coroutine
def block_loop(ready, done, blocking_transaction_active, times=1):
    for _ in range(times):
        yield from ready.wait()
        ready.clear()
        time.sleep(0.1)
        done.set()

    if blocking_transaction_active:
        yield from ready.wait()


@function_trace(name="waiter")
@asyncio.coroutine
def waiter(ready, done, times=1):
    for _ in range(times):
        ready.set()
        yield from done.wait()
        done.clear()


@background_task(name="wait")
@asyncio.coroutine
def wait_for_loop(ready, done, times=1):
    transaction = current_transaction()
    transaction._sampled = True

    # Run the waiter on another task so that the sentinel for wait appears
    # multiple times in the trace cache
    yield from asyncio.ensure_future(waiter(ready, done, times))

    # Set the ready to terminate the block_loop if it's running
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

    metric_count = 2 if event_loop_visibility_enabled else None
    execute_attributes = {
            'intrinsic': ('eventLoopTime',), 'agent': (), 'user': ()}
    wait_attributes = {
            'intrinsic': ('eventLoopWait',), 'agent': (), 'user': ()}
    if event_loop_visibility_enabled:
        wait_attributes = {'required_params': wait_attributes}
        execute_attributes = {'required_params': execute_attributes}
    else:
        wait_attributes = {'forgone_params': wait_attributes}
        execute_attributes = {'forgone_params': execute_attributes}

    scoped = (
        ("EventLoop/Wait/OtherTransaction/Function/block", metric_count),
    )
    rollup = (
        ("EventLoop/Wait/all", metric_count),
        ("EventLoop/Wait/allOther", metric_count),
    )

    ready, done = (asyncio.Event(), asyncio.Event())
    future = asyncio.gather(
        wait_for_loop(ready, done, 2),
        block_loop(ready, done, blocking_transaction_active, 2),
    )

    index = 0 if blocking_transaction_active else -1

    @override_application_settings({
        'event_loop_visibility.enabled': event_loop_visibility_enabled,
        'distributed_tracing.enabled': True,
    })
    @validate_transaction_trace_attributes(
        index=index + 1,
        **execute_attributes,
    )
    @validate_transaction_event_attributes(
        index=index,
        **wait_attributes,
    )
    @validate_transaction_event_attributes(
        index=index + 1,
        **execute_attributes,
    )
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


@override_application_settings({
    'event_loop_visibility.blocking_threshold': 0,
})
def test_record_event_loop_wait_outside_task():
    # Insert a random trace into the trace cache
    trace = FunctionTrace(name='testing')
    trace_cache()._cache[0] = trace

    @background_task(name='test_record_event_loop_wait_outside_task')
    def _test():
        yield

    for _ in _test():
        pass


@validate_transaction_metrics(
    "wait",
    background_task=True,
    rollup_metrics=(("EventLoop/Wait/all", None),),
)
def test_blocking_task_on_different_loop():
    loops = [asyncio.new_event_loop() for _ in range(2)]

    waiter_events = [asyncio.Event(loop=loops[0]) for _ in range(2)]
    waiter = wait_for_loop(*waiter_events, times=1)

    blocker_events = [asyncio.Event(loop=loops[1]) for _ in range(2)]
    blocker = block_loop(*blocker_events,
            blocking_transaction_active=False, times=1)

    waiter_task = loops[0].create_task(waiter)
    blocker_task = loops[1].create_task(blocker)

    # Set ready on the blocker
    blocker_events[0].set()

    loops[0].run_until_complete(waiter_events[0].wait())

    # Set done event for waiter
    waiter_events[1].set()

    loops[1].run_until_complete(blocker_task)
    loops[0].run_until_complete(waiter_task)


def test_record_event_loop_wait_on_different_task():
    import asyncio
    loop = asyncio.get_event_loop()

    async def recorder(ready, wait):
        ready.set()
        await wait.wait()
        trace_cache().record_event_loop_wait(0, 1)

    @background_task(name="test_record_event_loop_wait_on_different_task")
    async def transaction():
        coroutine_start, transaction_exit = asyncio.Event(), asyncio.Event()
        task = loop.create_task(recorder(coroutine_start, transaction_exit))
        await coroutine_start.wait()
        current_transaction().__exit__(None, None, None)
        transaction_exit.set()
        await task

    loop.run_until_complete(transaction())