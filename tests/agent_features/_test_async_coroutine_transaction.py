import asyncio
import pytest

from newrelic.core.config import global_settings
from newrelic.api.background_task import background_task
from newrelic.api.message_transaction import message_transaction
from newrelic.api.transaction import current_transaction

from testing_support.fixtures import (validate_transaction_errors,
        capture_transaction_metrics, override_generic_settings)

settings = global_settings()
loop = asyncio.get_event_loop()


def create_test_task(transaction, nr_enabled=True, does_hang=False,
        call_exit=False, runtime_error=False):
    @transaction
    async def task():
        txn = current_transaction()

        if not nr_enabled:
            assert txn is None

        if call_exit:
            txn.__exit__(None, None, None)

        try:
            if does_hang:
                await loop.create_future()
            else:
                await asyncio.sleep(0.0)
        except GeneratorExit:
            if runtime_error:
                await asyncio.sleep(0.0)

        if not call_exit:
            assert current_transaction() is txn

    return task


@pytest.mark.parametrize('transaction,metric', [
    (background_task(name='test'), 'OtherTransaction/Function/test'),
    (message_transaction('lib', 'dest_type', 'dest_name'),
            'OtherTransaction/Message/lib/dest_type/Named/dest_name'),
])
@pytest.mark.parametrize('nr_enabled,call_exit', (
        (False, False),
        (True, False),
        (True, True),
))
def test_async_coroutine_send(transaction, metric, call_exit, nr_enabled):
    metrics = []

    task_a = create_test_task(
            transaction, nr_enabled=nr_enabled, call_exit=call_exit)
    task_b = create_test_task(
            transaction, nr_enabled=nr_enabled, call_exit=call_exit)

    @override_generic_settings(settings, {'enabled': nr_enabled})
    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_send():
        loop = asyncio.get_event_loop()
        driver = asyncio.gather(task_a(), task_b())
        loop.run_until_complete(driver)

    _test_async_coroutine_send()

    if nr_enabled:
        assert metrics.count((metric, '')) == 2, metrics
    else:
        assert not metrics, metrics


@pytest.mark.parametrize('transaction,metric', [
    (background_task(name='test'), 'OtherTransaction/Function/test'),
    (message_transaction('lib', 'dest_type', 'dest_name'),
            'OtherTransaction/Message/lib/dest_type/Named/dest_name'),
])
def test_async_coroutine_send_disabled(transaction, metric):
    metrics = []

    task_a = create_test_task(transaction, call_exit=True)
    task_b = create_test_task(transaction, call_exit=True)

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_send():
        loop = asyncio.get_event_loop()
        driver = asyncio.gather(task_a(), task_b())
        loop.run_until_complete(driver)

    _test_async_coroutine_send()

    assert metrics.count((metric, '')) == 2, metrics


@pytest.mark.parametrize('transaction,metric', [
    (background_task(name='test'), 'OtherTransaction/Function/test'),
    (message_transaction('lib', 'dest_type', 'dest_name'),
            'OtherTransaction/Message/lib/dest_type/Named/dest_name'),
])
@validate_transaction_errors([])
def test_async_coroutine_throw_cancel(transaction, metric):
    metrics = []

    task_a = create_test_task(transaction)
    task_b = create_test_task(transaction)

    async def task_c():
        future_a = asyncio.ensure_future(task_a())
        future_b = asyncio.ensure_future(task_b())

        await asyncio.sleep(0.0)

        future_a.cancel()
        future_b.cancel()

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_throw_cancel():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_throw_cancel()

    assert metrics.count((metric, '')) == 2, metrics


@pytest.mark.parametrize('transaction,metric', [
    (background_task(name='test'), 'OtherTransaction/Function/test'),
    (message_transaction('lib', 'dest_type', 'dest_name'),
            'OtherTransaction/Message/lib/dest_type/Named/dest_name'),
])
@validate_transaction_errors(['builtins:ValueError'])
def test_async_coroutine_throw_error(transaction, metric):
    metrics = []

    task_a = create_test_task(transaction)
    task_b = create_test_task(transaction)

    async def task_c():
        coro_a = task_a()
        coro_b = task_b()

        with pytest.raises(ValueError):
            coro_a.throw(ValueError)
        with pytest.raises(ValueError):
            coro_b.throw(ValueError)

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_throw_error():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_throw_error()

    assert metrics.count((metric, '')) == 2, metrics
    assert metrics.count(('Errors/' + metric, '')) == 2, metrics
    assert metrics.count(('Errors/all', '')) == 2, metrics


@pytest.mark.parametrize('transaction,metric', [
    (background_task(name='test'), 'OtherTransaction/Function/test'),
    (message_transaction('lib', 'dest_type', 'dest_name'),
            'OtherTransaction/Message/lib/dest_type/Named/dest_name'),
])
@pytest.mark.parametrize('start_coroutines', (False, True))
def test_async_coroutine_close(transaction, metric, start_coroutines):
    metrics = []

    task_a = create_test_task(transaction)
    task_b = create_test_task(transaction)

    async def task_c():
        coro_a = task_a()
        coro_b = task_b()

        if start_coroutines:
            asyncio.ensure_future(coro_a)
            asyncio.ensure_future(coro_b)

            await asyncio.sleep(0.0)

        coro_a.close()
        coro_b.close()

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_close():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_close()

    if start_coroutines:
        assert metrics.count((metric, '')) == 2, metrics
    else:
        assert not metrics


@pytest.mark.parametrize('transaction,metric', [
    (background_task(name='test'), 'OtherTransaction/Function/test'),
    (message_transaction('lib', 'dest_type', 'dest_name'),
            'OtherTransaction/Message/lib/dest_type/Named/dest_name'),
])
@validate_transaction_errors(['builtins:RuntimeError'])
def test_async_coroutine_close_raises_error(transaction, metric):
    metrics = []

    task_a = create_test_task(transaction, runtime_error=True)
    task_b = create_test_task(transaction, runtime_error=True)

    async def task_c():
        coro_a = task_a()
        coro_b = task_b()

        asyncio.ensure_future(coro_a)
        asyncio.ensure_future(coro_b)

        await asyncio.sleep(0.0)

        with pytest.raises(RuntimeError):
            coro_a.close()

        with pytest.raises(RuntimeError):
            coro_b.close()

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_close_raises_error():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_close_raises_error()

    assert metrics.count((metric, '')) == 2, metrics
    assert metrics.count(('Errors/all', '')) == 2, metrics
