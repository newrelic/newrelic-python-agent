import pytest
from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.function_trace import function_trace
from newrelic.core.trace_cache import trace_cache


@function_trace(name='waiter')
async def waiter(asyncio, event, wait):
    event.set()

    # Block until the parent says to exit
    await wait.wait()


async def task(asyncio, trace, event, wait):
    # Test that the trace has been propagated onto this task
    assert current_trace() is trace

    # Start a function trace, this should not interfere with context in the
    # parent task
    await waiter(asyncio, event, wait)


@background_task(name='test_context_propagation')
async def _test(asyncio, schedule):
    trace = current_trace()
    assert trace is not None

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


@pytest.mark.parametrize('schedule', ('create_task', 'ensure_future'))
def test_context_propagation(schedule):
    import asyncio
    loop = asyncio.get_event_loop()

    schedule = getattr(asyncio, schedule, None) or getattr(loop, schedule)

    # Keep the trace around so that it's not removed from the trace cache
    # through reference counting (for testing)
    _ = loop.run_until_complete(_test(asyncio, schedule))

    # The agent should have removed all traces from the cache since
    # run_until_complete has terminated (all callbacks scheduled inside the
    # task have run)
    assert not trace_cache()._cache
