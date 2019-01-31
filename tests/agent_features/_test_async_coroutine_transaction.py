import asyncio
import pytest

from newrelic.core.config import global_settings
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

from testing_support.fixtures import (validate_transaction_errors,
        capture_transaction_metrics, override_generic_settings)

settings = global_settings()
loop = asyncio.get_event_loop()


def check_transaction(name, txn_enabled):
    txn = current_transaction()

    if txn_enabled:
        assert txn.name == name
    else:
        assert not txn

    return txn


def create_test_task(name, txn_enabled=True, does_hang=False, call_exit=False):
    @background_task(name=name)
    async def task():
        txn = check_transaction(name, txn_enabled)

        if call_exit:
            txn.__exit__(None, None, None)

        if does_hang:
            await loop.create_future()
        else:
            await asyncio.sleep(0.0)

        if not call_exit:
            check_transaction(name, txn_enabled)

    return task


@pytest.mark.parametrize('nr_enabled,call_exit', (
        (False, False),
        (True, False),
        (True, True),
))
def test_async_coroutine_background_send(call_exit, nr_enabled):
    metrics = []

    task_a = create_test_task(
            'task_a', txn_enabled=nr_enabled, call_exit=call_exit)
    task_b = create_test_task(
            'task_b', txn_enabled=nr_enabled, call_exit=call_exit)

    @override_generic_settings(settings, {'enabled': nr_enabled})
    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_background_send():
        loop = asyncio.get_event_loop()
        driver = asyncio.gather(task_a(), task_b())
        loop.run_until_complete(driver)

    _test_async_coroutine_background_send()

    if nr_enabled:
        assert metrics.count(('OtherTransaction/Function/task_a', '')) == 1, \
                metrics
        assert metrics.count(('OtherTransaction/Function/task_b', '')) == 1, \
                metrics
    else:
        assert not metrics, metrics


def test_async_coroutine_background_send_disabled():
    metrics = []

    task_a = create_test_task('task_a', call_exit=True)
    task_b = create_test_task('task_b', call_exit=True)

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_background_send():
        loop = asyncio.get_event_loop()
        driver = asyncio.gather(task_a(), task_b())
        loop.run_until_complete(driver)

    _test_async_coroutine_background_send()

    assert metrics.count(('OtherTransaction/Function/task_a', '')) == 1, \
                metrics
    assert metrics.count(('OtherTransaction/Function/task_b', '')) == 1, \
                metrics


@validate_transaction_errors([])
def test_async_coroutine_background_throw_cancel():
    metrics = []

    task_a = create_test_task('task_a', True)
    task_b = create_test_task('task_b', True)

    async def task_c():
        future_a = asyncio.ensure_future(task_a())
        future_b = asyncio.ensure_future(task_b())

        await asyncio.sleep(0.0)

        future_a.cancel()
        future_b.cancel()

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_background_throw_cancel():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_background_throw_cancel()

    assert metrics.count(('OtherTransaction/Function/task_a', '')) == 1, \
                metrics
    assert metrics.count(('OtherTransaction/Function/task_b', '')) == 1, \
                metrics


@validate_transaction_errors(['builtins:ValueError'])
def test_async_coroutine_background_throw_error():
    metrics = []

    task_a = create_test_task('task_a', True)
    task_b = create_test_task('task_b', True)

    async def task_c():
        coro_a = task_a()
        coro_b = task_b()

        with pytest.raises(ValueError):
            coro_a.throw(ValueError)
        with pytest.raises(ValueError):
            coro_b.throw(ValueError)

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_background_throw_error():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_background_throw_error()

    assert metrics.count(('OtherTransaction/Function/task_a', '')) == 1, \
                metrics
    assert metrics.count(('OtherTransaction/Function/task_b', '')) == 1, \
                metrics
    assert metrics.count(
            ('Errors/OtherTransaction/Function/task_a', '')) == 1, metrics
    assert metrics.count(
            ('Errors/OtherTransaction/Function/task_b', '')) == 1, metrics
    assert metrics.count(('Errors/all', '')) == 2, metrics


@pytest.mark.parametrize('start_coroutines', (False, True))
def test_async_coroutine_background_close(start_coroutines):
    metrics = []

    task_a = create_test_task('task_a', True)
    task_b = create_test_task('task_b', True)

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
    def _test_async_coroutine_background_close_before_start():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_background_close_before_start()

    if start_coroutines:
        assert metrics.count(('OtherTransaction/Function/task_a', '')) == 1, \
                metrics
        assert metrics.count(('OtherTransaction/Function/task_b', '')) == 1, \
                metrics
    else:
        assert not metrics


@background_task(name='generate_runtime_error')
async def generate_runtime_error():
    try:
        await asyncio.sleep(0.0)
    except GeneratorExit:
        await asyncio.sleep(0.0)


@validate_transaction_errors(['builtins:RuntimeError'])
def test_async_coroutine_background_close_raises_error():
    metrics = []

    async def task_c():
        coro_a = generate_runtime_error()
        coro_b = generate_runtime_error()

        asyncio.ensure_future(coro_a)
        asyncio.ensure_future(coro_b)

        await asyncio.sleep(0.0)

        with pytest.raises(RuntimeError):
            coro_a.close()

        with pytest.raises(RuntimeError):
            coro_b.close()

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_background_close_raises_error():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task_c())

    _test_async_coroutine_background_close_raises_error()

    assert metrics.count(
        ('OtherTransaction/Function/generate_runtime_error', '')) == 2, metrics
    assert metrics.count(('Errors/all', '')) == 2, metrics
