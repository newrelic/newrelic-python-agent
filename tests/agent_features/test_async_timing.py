import pytest
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import function_wrapper
from newrelic.api.background_task import background_task, BackgroundTask
from newrelic.api.function_trace import function_trace
from testing_support.fixtures import capture_transaction_metrics
from testing_support.validators.validate_transaction_count import (
        validate_transaction_count)

asyncio = pytest.importorskip('asyncio')


def validate_total_time_value_greater_than(value, concurrent=False):

    @function_wrapper
    def _validate_total_time_value(wrapped, instance, args, kwargs):
        metrics = {}
        result = capture_transaction_metrics([], metrics)(
                wrapped)(*args, **kwargs)
        total_time = metrics[('OtherTransactionTotalTime', '')][1]
        # Assert total call time is at least that value
        assert total_time >= value

        duration = metrics[('OtherTransaction/all', '')][1]
        if concurrent:
            # If there is concurrent work, the total_time must be strictly
            # greater than the duration
            assert total_time > duration
        else:
            assert total_time == duration
        return result

    return _validate_total_time_value


@function_trace(name='child')
@asyncio.coroutine
def child():
    yield from asyncio.sleep(0.1)


@function_trace(name='parent')
@asyncio.coroutine
def parent(calls):
    coros = [child() for _ in range(calls)]
    yield from asyncio.gather(*coros)
    yield from asyncio.sleep(0.1)


@validate_total_time_value_greater_than(0.2)
@background_task(name='test_total_time_sync')
def test_total_time_sync():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(parent(1))


@validate_total_time_value_greater_than(0.3, concurrent=True)
@background_task(name='test_total_time_sync')
def test_total_time_async():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(parent(2))


@asyncio.coroutine
def transaction():
    application = application_instance()
    with BackgroundTask(application, 'transaction'):
        yield from asyncio.sleep(0)


@asyncio.coroutine
def parent_transaction():
    yield from asyncio.gather(transaction(), transaction())


@validate_transaction_count(2)
def test_async_context_managers():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(parent_transaction())
