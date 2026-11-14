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

import asyncio
import gc
import threading
import weakref

import pytest

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.llm_utils import AsyncLLMStreamProxy, LLMStreamProxy
from newrelic.core.trace_cache import trace_cache

# ====================
#       Fixtures
# ====================


@pytest.fixture
def on_stop_iteration_event():
    event = threading.Event()
    return event


@pytest.fixture
def on_stop_iteration(on_stop_iteration_event):
    def _on_stop_iteration(self, transaction):
        on_stop_iteration_event.set()

    return _on_stop_iteration


@pytest.fixture
def on_error_event():
    event = threading.Event()
    return event


@pytest.fixture
def on_error(on_error_event):
    def _on_error(self, transaction):
        on_error_event.set()

    return _on_error


@pytest.fixture
def stream_proxy(on_stop_iteration, on_error):
    def _stream_proxy(generator):
        return LLMStreamProxy(generator, on_stop_iteration=on_stop_iteration, on_error=on_error)

    return _stream_proxy


@pytest.fixture
def async_stream_proxy(on_stop_iteration, on_error):
    def _async_stream_proxy(async_generator):
        return AsyncLLMStreamProxy(async_generator, on_stop_iteration=on_stop_iteration, on_error=on_error)

    return _async_stream_proxy


# ====================
#        Tests
# ====================


@background_task()
def test_llm_stream_proxy_on_stop_iteration(stream_proxy, on_stop_iteration_event, on_error_event):
    def gen():
        yield from range(4)

    proxy = stream_proxy(gen())
    results = list(proxy)
    assert results == [0, 1, 2, 3]
    assert on_stop_iteration_event.is_set()
    assert not on_error_event.is_set()


@background_task()
def test_async_llm_stream_proxy_on_stop_iteration(
    event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event
):
    async def agen():
        for i in range(4):
            yield i

    async def _test():
        proxy = async_stream_proxy(agen())
        results = [x async for x in proxy]
        assert results == [0, 1, 2, 3]
        assert on_stop_iteration_event.is_set()
        assert not on_error_event.is_set()

    event_loop.run_until_complete(_test())


@background_task()
def test_llm_stream_proxy_on_close(stream_proxy, on_stop_iteration_event, on_error_event):
    def gen():
        yield from range(4)

    proxy = stream_proxy(gen())
    iterator = iter(proxy)
    next(iterator)  # Start the generator so we can manipulate it
    iterator.close()  # Close the iterator to trigger on_stop_iteration early

    assert on_stop_iteration_event.is_set()
    assert not on_error_event.is_set()


@background_task()
def test_async_llm_stream_proxy_on_close(event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event):
    async def agen():
        for i in range(4):
            yield i

    async def _test():
        proxy = async_stream_proxy(agen())
        iterator = proxy.__aiter__()
        await iterator.__anext__()  # Start the generator so we can manipulate it
        await iterator.aclose()  # Close the iterator to trigger on_stop_iteration early

        assert on_stop_iteration_event.is_set()
        assert not on_error_event.is_set()

    event_loop.run_until_complete(_test())


@background_task()
def test_llm_stream_proxy_on_error(stream_proxy, on_stop_iteration_event, on_error_event):
    def gen():
        yield 1
        raise RuntimeError

    proxy = stream_proxy(gen())
    with pytest.raises(RuntimeError):
        _results = list(proxy)
    assert on_error_event.is_set()
    assert not on_stop_iteration_event.is_set()


@background_task()
def test_async_llm_stream_proxy_on_error(event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event):
    async def agen():
        yield 1
        raise RuntimeError

    async def _test():
        proxy = async_stream_proxy(agen())
        with pytest.raises(RuntimeError):
            _results = [x async for x in proxy]
        assert on_error_event.is_set()
        assert not on_stop_iteration_event.is_set()

    event_loop.run_until_complete(_test())


@background_task()
def test_llm_stream_proxy_on_throw(stream_proxy, on_stop_iteration_event, on_error_event):
    def gen():
        yield from range(4)

    proxy = stream_proxy(gen())
    iterator = iter(proxy)
    next(iterator)  # Start the generator so we can manipulate it
    with pytest.raises(RuntimeError):
        iterator.throw(RuntimeError)  # Throw an exception in the generator to trigger on_error early

    assert on_error_event.is_set()
    assert not on_stop_iteration_event.is_set()


@background_task()
def test_async_llm_stream_proxy_on_throw(event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event):
    async def agen():
        for i in range(4):
            yield i

    async def _test():
        proxy = async_stream_proxy(agen())
        iterator = proxy.__aiter__()
        await iterator.__anext__()  # Start the generator so we can manipulate it
        with pytest.raises(RuntimeError):
            await iterator.athrow(RuntimeError)  # Throw an exception in the generator to trigger on_error early

        assert on_error_event.is_set()
        assert not on_stop_iteration_event.is_set()

    event_loop.run_until_complete(_test())


@pytest.mark.parametrize("exit_early", ["break", "raise"])
@background_task()
def test_async_llm_stream_proxy_on_task_done_after_abandoned(
    event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event, exit_early
):
    async def agen():
        for i in range(4):
            yield i

    async def consume():
        proxy = async_stream_proxy(agen())
        async for _ in proxy:
            if exit_early == "break":
                break
            raise RuntimeError

    async def _test():
        task = asyncio.create_task(consume())
        if exit_early == "raise":
            with pytest.raises(RuntimeError):
                await task
        else:
            await task
        await asyncio.sleep(0)  # The task's done callbacks run after the awaiting task resumes.

        assert on_stop_iteration_event.is_set()
        assert not on_error_event.is_set()

    event_loop.run_until_complete(_test())


@background_task()
def test_async_llm_stream_proxy_on_task_done_exits_the_stream_trace(event_loop):
    async def agen():
        for i in range(4):
            yield i

    async def consume():
        # Like the instrumentation hooks: the stream's trace is entered when the stream is created and
        # exited from on_stop_iteration.
        trace = FunctionTrace(name="stream")
        trace.__enter__()
        proxy = AsyncLLMStreamProxy(
            agen(),
            on_stop_iteration=lambda proxy, transaction: trace.__exit__(None, None, None),
            on_error=lambda proxy, transaction: trace.__exit__(None, None, None),
        )
        async for _ in proxy:
            break
        return trace

    async def _test():
        task = asyncio.create_task(consume())
        trace = await task
        await asyncio.sleep(0)

        assert trace.exited
        # Exiting the trace from the done callback must not leave a cache entry for the finished task,
        # which a later task reusing its id would inherit.
        assert id(task) not in trace_cache()

    event_loop.run_until_complete(_test())


@pytest.mark.parametrize("finish", ["exhausted", "aclose"])
@background_task()
def test_async_llm_stream_proxy_reports_once_when_finished_in_task(event_loop, finish):
    stops = []

    async def agen():
        for i in range(4):
            yield i

    async def consume():
        proxy = AsyncLLMStreamProxy(
            agen(), on_stop_iteration=lambda proxy, transaction: stops.append(transaction), on_error=None
        )
        if finish == "exhausted":
            _results = [x async for x in proxy]
        else:
            await proxy.__anext__()
            await proxy.aclose()

    async def _test():
        await asyncio.create_task(consume())
        await asyncio.sleep(0)

        assert len(stops) == 1

    event_loop.run_until_complete(_test())


@background_task()
def test_async_llm_stream_proxy_consumed_in_another_task_is_not_finished_by_its_creator(
    event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event
):
    async def agen():
        for i in range(4):
            yield i

    async def create():
        return async_stream_proxy(agen())

    async def _test():
        proxy = await asyncio.create_task(create())
        await asyncio.sleep(0)

        assert not on_stop_iteration_event.is_set()

        results = [x async for x in proxy]
        assert results == [0, 1, 2, 3]
        assert on_stop_iteration_event.is_set()
        assert not on_error_event.is_set()

    event_loop.run_until_complete(_test())


def test_async_llm_stream_proxy_abandoned_in_transaction_task_is_not_finished_after_transaction(
    event_loop, async_stream_proxy, on_stop_iteration_event, on_error_event
):
    async def agen():
        for i in range(4):
            yield i

    @background_task()
    async def consume():
        proxy = async_stream_proxy(agen())
        async for _ in proxy:
            break

    async def _test():
        await asyncio.create_task(consume())
        await asyncio.sleep(0)

        # The transaction was recorded before its task finished, so there is nothing left to report into.
        assert not on_stop_iteration_event.is_set()
        assert not on_error_event.is_set()

    event_loop.run_until_complete(_test())


def test_async_llm_stream_proxy_abandoned_in_child_task_finishes_before_awaiting_task_resumes(event_loop):
    states = []

    async def agen():
        for i in range(4):
            yield i

    async def consume():
        proxy = AsyncLLMStreamProxy(
            agen(), on_stop_iteration=lambda proxy, transaction: states.append(transaction.state), on_error=None
        )
        async for _ in proxy:
            break

    @background_task()
    async def transaction():
        with FunctionTrace(name="tool"):
            # The transaction ends as soon as this resumes, so the stream must be finished before then.
            await asyncio.create_task(consume())

    event_loop.run_until_complete(transaction())

    assert len(states) == 1
    assert states[0] == 1  # Transaction.STATE_RUNNING


@pytest.mark.parametrize("abandon", [False, True])
def test_async_llm_stream_proxy_does_not_accumulate_in_long_lived_task(event_loop, abandon):
    # A long-lived task running a transaction per unit of work, like a queue consumer.
    async def agen():
        for i in range(4):
            yield i

    async def worker():
        refs = []
        for _ in range(10):

            @background_task()
            async def unit():
                proxy = AsyncLLMStreamProxy(agen(), on_stop_iteration=lambda proxy, transaction: None, on_error=None)
                refs.append(weakref.ref(proxy))
                async for _ in proxy:
                    if abandon:
                        break

            await unit()

        gc.collect()
        assert not trace_cache()._task_stop_callbacks.get(id(asyncio.current_task()))
        assert all(ref() is None for ref in refs)

    event_loop.run_until_complete(worker())


@background_task()
def test_async_llm_stream_proxy_unregisters_when_finished_in_child_task(event_loop):
    async def agen():
        for i in range(4):
            yield i

    async def consume():
        proxy = AsyncLLMStreamProxy(agen(), on_stop_iteration=lambda proxy, transaction: None, on_error=None)
        _results = [x async for x in proxy]
        assert not trace_cache()._task_stop_callbacks.get(id(asyncio.current_task()))

    event_loop.run_until_complete(consume())


def test_task_stop_callbacks_are_removed_for_tasks_outside_the_instrumented_loop(event_loop):
    calls = []

    async def noop():
        pass

    async def _test():
        # Constructing a Task directly bypasses the instrumented create_task, so task_stop never runs for it.
        task = asyncio.Task(noop())
        trace_cache().add_task_stop_callback(task, calls.append)
        await task
        await asyncio.sleep(0)

        assert calls == [task]
        assert id(task) not in trace_cache()._task_stop_callbacks

    event_loop.run_until_complete(_test())
