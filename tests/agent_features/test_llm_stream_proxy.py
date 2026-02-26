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

import gc
import threading

import pytest

from newrelic.api.background_task import background_task
from newrelic.common.llm_utils import AsyncLLMStreamProxy, LLMStreamProxy

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
