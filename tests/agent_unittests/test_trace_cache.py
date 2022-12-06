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

import threading

import pytest

from newrelic.core.trace_cache import TraceCache

_TEST_CONCURRENT_ITERATION_TC_SIZE = 20


class DummyTrace(object):
    pass


@pytest.fixture(scope="function")
def trace_cache():
    return TraceCache()


def test_trace_cache_methods(trace_cache):
    """Test MutableMapping methods functional for trace_cache"""
    obj = DummyTrace()  # weakref compatible object

    trace_cache[1] = obj
    assert 1 in trace_cache
    assert bool(trace_cache)
    assert list(trace_cache)

    del trace_cache[1]
    assert 1 not in trace_cache
    assert not bool(trace_cache)

    trace_cache[1] = obj
    assert trace_cache.get(1, None)
    assert trace_cache.pop(1, None)

    trace_cache[1] = obj
    assert len(trace_cache) == 1
    assert len(list(trace_cache.items())) == 1
    assert len(list(trace_cache.keys())) == 1
    assert len(list(trace_cache.values())) == 1


@pytest.fixture(scope="function")
def iterate_trace_cache(trace_cache):
    def _iterate_trace_cache(shutdown):
        while True:
            if shutdown.is_set():
                return
            for k, v in trace_cache.items():
                pass
            for v in trace_cache.values():
                pass
            for v in trace_cache.keys():
                pass

    return _iterate_trace_cache


@pytest.fixture(scope="function")
def change_weakref_dict_size(trace_cache):
    def _change_weakref_dict_size(shutdown, obj_refs):
        """
        Cause RuntimeErrors when iterating on the trace_cache by:
          - Repeatedly pop and add batches of keys to cause size changes.
          - Randomly delete and replace some object refs so the weak references are deleted,
            causing the weakref dict to delete them and forcing further size changes.
        """

        dict_size_change = _TEST_CONCURRENT_ITERATION_TC_SIZE // 2  # Remove up to half of items
        while True:
            if shutdown.is_set():
                return

            # Delete and re-add keys
            for i in range(dict_size_change):
                trace_cache._cache.pop(i, None)
            for i in range(dict_size_change):
                trace_cache._cache[i] = obj_refs[i]

            # Replace every 3rd obj ref causing the WeakValueDictionary to drop it.
            for i, _ in enumerate(obj_refs[::3]):
                obj_refs[i] = DummyTrace()

    return _change_weakref_dict_size


def test_concurrent_iteration(iterate_trace_cache, change_weakref_dict_size):
    """
    Test for exceptions related to trace_cache changing size during iteration.

    The WeakValueDictionary used internally is particularly prone to this, as iterating
    on it in any way other than indirectly through WeakValueDictionary.valuerefs()
    will cause RuntimeErrors due to the unguarded iteration on a dictionary internally.
    """
    obj_refs = [DummyTrace() for _ in range(_TEST_CONCURRENT_ITERATION_TC_SIZE)]
    shutdown = threading.Event()

    t1 = threading.Thread(target=change_weakref_dict_size, args=(shutdown, obj_refs))
    t2 = threading.Thread(target=iterate_trace_cache, args=(shutdown,))
    t1.daemon = True
    t2.daemon = True
    t1.start()
    t2.start()

    # Run for 1 second, then shutdown. Stop immediately for exceptions.
    t2.join(timeout=1)
    assert t1.is_alive(), "Thread exited with exception."
    assert t2.is_alive(), "Thread exited with exception."
    shutdown.set()

    # Ensure threads shutdown with a timeout to prevent hangs
    t1.join(timeout=1)
    t2.join(timeout=1)
    assert not t1.is_alive(), "Thread failed to exit."
    assert not t2.is_alive(), "Thread failed to exit."
