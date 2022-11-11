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
import sys

import pytest
from testing_support.fixtures import (
    capture_transaction_metrics,
    override_generic_settings,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.message_transaction import message_transaction
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import web_transaction
from newrelic.core.config import global_settings

if sys.version_info >= (3, 5):
    from _test_async_coroutine_transaction import native_coroutine_test
else:
    native_coroutine_test = None

settings = global_settings()


def coroutine_test(event_loop, transaction, nr_enabled=True, does_hang=False, call_exit=False, runtime_error=False):
    @transaction
    async def task():
        txn = current_transaction()

        if not nr_enabled:
            assert txn is None
        else:
            assert txn._loop_time == 0.0

        if call_exit:
            txn.__exit__(None, None, None)
        else:
            assert current_transaction() is txn

        try:
            if does_hang:
                await loop.create_future()  # noqa
            else:
                await asyncio.sleep(0.0)
                if nr_enabled and txn.enabled:
                    # Validate loop time is recorded after suspend
                    assert txn._loop_time > 0.0
        except GeneratorExit:
            if runtime_error:
                await asyncio.sleep(0.0)

    return task


test_matrix = [coroutine_test]
if native_coroutine_test:
    test_matrix.append(native_coroutine_test)


@pytest.mark.parametrize("num_coroutines", (2,))
@pytest.mark.parametrize("create_test_task", test_matrix)
@pytest.mark.parametrize(
    "transaction,metric",
    [
        (background_task(name="test"), "OtherTransaction/Function/test"),
        (
            message_transaction("lib", "dest_type", "dest_name"),
            "OtherTransaction/Message/lib/dest_type/Named/dest_name",
        ),
    ],
)
@pytest.mark.parametrize(
    "nr_enabled,call_exit",
    (
        (False, False),
        (True, False),
        (True, True),
    ),
)
def test_async_coroutine_send(event_loop, num_coroutines, create_test_task, transaction, metric, call_exit, nr_enabled):
    metrics = []

    tasks = [
        create_test_task(event_loop, transaction, nr_enabled=nr_enabled, call_exit=call_exit)
        for _ in range(num_coroutines)
    ]

    @override_generic_settings(settings, {"enabled": nr_enabled})
    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_send():
        driver = asyncio.gather(*[t() for t in tasks])
        event_loop.run_until_complete(driver)

    _test_async_coroutine_send()

    if nr_enabled:
        assert metrics.count((metric, "")) == num_coroutines, metrics
    else:
        assert not metrics, metrics


@pytest.mark.parametrize("num_coroutines", (2,))
@pytest.mark.parametrize("create_test_task", test_matrix)
@pytest.mark.parametrize(
    "transaction,metric",
    [
        (background_task(name="test"), "OtherTransaction/Function/test"),
        (
            message_transaction("lib", "dest_type", "dest_name"),
            "OtherTransaction/Message/lib/dest_type/Named/dest_name",
        ),
    ],
)
def test_async_coroutine_send_disabled(event_loop, num_coroutines, create_test_task, transaction, metric):
    metrics = []

    tasks = [create_test_task(event_loop, transaction, call_exit=True) for _ in range(num_coroutines)]

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_send():
        driver = asyncio.gather(*[t() for t in tasks])
        event_loop.run_until_complete(driver)

    _test_async_coroutine_send()

    assert metrics.count((metric, "")) == num_coroutines, metrics


@pytest.mark.parametrize("num_coroutines", (2,))
@pytest.mark.parametrize("create_test_task", test_matrix)
@pytest.mark.parametrize(
    "transaction,metric",
    [
        (background_task(name="test"), "OtherTransaction/Function/test"),
        (
            message_transaction("lib", "dest_type", "dest_name"),
            "OtherTransaction/Message/lib/dest_type/Named/dest_name",
        ),
    ],
)
@validate_transaction_errors([])
def test_async_coroutine_throw_cancel(event_loop, num_coroutines, create_test_task, transaction, metric):
    metrics = []

    tasks = [create_test_task(event_loop, transaction) for _ in range(num_coroutines)]

    async def task_c():
        futures = [asyncio.ensure_future(t()) for t in tasks]

        await asyncio.sleep(0.0)

        [f.cancel() for f in futures]

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_throw_cancel():
        event_loop.run_until_complete(task_c())

    _test_async_coroutine_throw_cancel()

    assert metrics.count((metric, "")) == num_coroutines, metrics


@pytest.mark.parametrize("num_coroutines", (2,))
@pytest.mark.parametrize("create_test_task", test_matrix)
@pytest.mark.parametrize(
    "transaction,metric",
    [
        (background_task(name="test"), "OtherTransaction/Function/test"),
        (
            message_transaction("lib", "dest_type", "dest_name"),
            "OtherTransaction/Message/lib/dest_type/Named/dest_name",
        ),
    ],
)
@validate_transaction_errors(["builtins:ValueError"])
def test_async_coroutine_throw_error(event_loop, num_coroutines, create_test_task, transaction, metric):
    metrics = []

    tasks = [create_test_task(event_loop, transaction) for _ in range(num_coroutines)]

    async def task_c():
        coros = [t() for t in tasks]

        for coro in coros:
            with pytest.raises(ValueError):
                coro.throw(ValueError)

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_throw_error():
        event_loop.run_until_complete(task_c())

    _test_async_coroutine_throw_error()

    assert metrics.count((metric, "")) == num_coroutines, metrics
    assert metrics.count(("Errors/" + metric, "")) == num_coroutines, metrics
    assert metrics.count(("Errors/all", "")) == num_coroutines, metrics


@pytest.mark.parametrize("num_coroutines", (1,))
@pytest.mark.parametrize("create_test_task", test_matrix)
@pytest.mark.parametrize(
    "transaction,metric",
    [
        (background_task(name="test"), "OtherTransaction/Function/test"),
        (
            message_transaction("lib", "dest_type", "dest_name"),
            "OtherTransaction/Message/lib/dest_type/Named/dest_name",
        ),
    ],
)
@pytest.mark.parametrize("start_coroutines", (False, True))
def test_async_coroutine_close(event_loop, num_coroutines, create_test_task, transaction, metric, start_coroutines):
    metrics = []

    tasks = [create_test_task(event_loop, transaction) for _ in range(num_coroutines)]

    async def task_c():
        coros = [t() for t in tasks]

        if start_coroutines:
            [asyncio.ensure_future(coro) for coro in coros]

            await asyncio.sleep(0.0)

        [coro.close() for coro in coros]

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_close():
        event_loop.run_until_complete(task_c())

    _test_async_coroutine_close()

    if start_coroutines:
        assert metrics.count((metric, "")) == num_coroutines, metrics
    else:
        assert not metrics


@pytest.mark.parametrize("num_coroutines", (1,))
@pytest.mark.parametrize("create_test_task", test_matrix)
@pytest.mark.parametrize(
    "transaction,metric",
    [
        (background_task(name="test"), "OtherTransaction/Function/test"),
        (
            message_transaction("lib", "dest_type", "dest_name"),
            "OtherTransaction/Message/lib/dest_type/Named/dest_name",
        ),
    ],
)
@validate_transaction_errors(["builtins:RuntimeError"])
def test_async_coroutine_close_raises_error(event_loop, num_coroutines, create_test_task, transaction, metric):
    metrics = []

    tasks = [create_test_task(event_loop, transaction, runtime_error=True) for _ in range(num_coroutines)]

    async def task_c():
        coros = [t() for t in tasks]

        [c.send(None) for c in coros]

        await asyncio.sleep(0.0)

        for coro in coros:
            with pytest.raises(RuntimeError):
                coro.close()

    @capture_transaction_metrics(metrics)
    def _test_async_coroutine_close_raises_error():
        event_loop.run_until_complete(task_c())

    _test_async_coroutine_close_raises_error()

    assert metrics.count((metric, "")) == num_coroutines, metrics
    assert metrics.count(("Errors/all", "")) == num_coroutines, metrics


@pytest.mark.parametrize(
    "transaction,metric,arguments",
    [
        (web_transaction, "Apdex/Function/%s", lambda name: ([], {"name": name})),
        (
            message_transaction,
            "OtherTransaction/Message/lib/dest_type/Named/%s",
            lambda name: (["lib", "dest_type", name], {}),
        ),
        (background_task, "OtherTransaction/Function/%s", lambda name: ([], {"name": name})),
    ],
)
def test_deferred_async_background_task(event_loop, transaction, metric, arguments):
    deferred_metric = (metric % "deferred", "")

    args, kwargs = arguments("deferred")

    @transaction(*args, **kwargs)
    async def child_task():
        await asyncio.sleep(0)

    main_metric = (metric % "main", "")

    args, kwargs = arguments("main")

    @transaction(*args, **kwargs)
    async def parent_task():
        await asyncio.sleep(0)
        return event_loop.create_task(child_task())

    async def test_runner():
        child = await parent_task()
        await child

    metrics = []

    @capture_transaction_metrics(metrics)
    def _test():
        event_loop.run_until_complete(test_runner())

    _test()

    assert main_metric in metrics
    assert deferred_metric in metrics


@pytest.mark.parametrize(
    "transaction,metric,arguments",
    [
        (web_transaction, "Apdex/Function/%s", lambda name: ([], {"name": name})),
        (
            message_transaction,
            "OtherTransaction/Message/lib/dest_type/Named/%s",
            lambda name: (["lib", "dest_type", name], {}),
        ),
        (background_task, "OtherTransaction/Function/%s", lambda name: ([], {"name": name})),
    ],
)
def test_child_transaction_when_parent_is_running(event_loop, transaction, metric, arguments):
    deferred_metric = (metric % "deferred", "")

    args, kwargs = arguments("deferred")

    @transaction(*args, **kwargs)
    async def child_task():
        await asyncio.sleep(0)

    main_metric = (metric % "main", "")

    args, kwargs = arguments("main")

    @transaction(*args, **kwargs)
    async def parent_task():
        await event_loop.create_task(child_task())

    metrics = []

    @capture_transaction_metrics(metrics)
    def _test():
        event_loop.run_until_complete(parent_task())

    _test()

    assert main_metric in metrics
    assert deferred_metric in metrics


@pytest.mark.parametrize(
    "transaction,metric,arguments",
    [
        (web_transaction, "Apdex/Function/%s", lambda name: ([], {"name": name})),
        (
            message_transaction,
            "OtherTransaction/Message/lib/dest_type/Named/%s",
            lambda name: (["lib", "dest_type", name], {}),
        ),
        (background_task, "OtherTransaction/Function/%s", lambda name: ([], {"name": name})),
    ],
)
def test_nested_coroutine_inside_sync(event_loop, transaction, metric, arguments):
    child_metric = (metric % "child", "")

    args, kwargs = arguments("child")

    @transaction(*args, **kwargs)
    async def child_task():
        await asyncio.sleep(0)

    main_metric = (metric % "main", "")
    args, kwargs = arguments("main")

    metrics = []

    @capture_transaction_metrics(metrics)
    @transaction(*args, **kwargs)
    def parent():
        event_loop.run_until_complete(child_task())

    parent()

    assert main_metric in metrics
    assert child_metric not in metrics


@pytest.mark.parametrize(
    "transaction,metric,arguments",
    [
        (web_transaction, "Apdex/Function/%s", lambda name: ([], {"name": name})),
        (
            message_transaction,
            "OtherTransaction/Message/lib/dest_type/Named/%s",
            lambda name: (["lib", "dest_type", name], {}),
        ),
        (background_task, "OtherTransaction/Function/%s", lambda name: ([], {"name": name})),
    ],
)
def test_nested_coroutine_task_already_active(event_loop, transaction, metric, arguments):
    deferred_metric = (metric % "deferred", "")

    args, kwargs = arguments("deferred")

    @transaction(*args, **kwargs)
    async def child_task():
        await asyncio.sleep(0)

    @function_trace()
    async def child_trace():
        await child_task()

    main_metric = (metric % "main", "")

    args, kwargs = arguments("main")

    @transaction(*args, **kwargs)
    async def parent_task():
        await event_loop.create_task(child_trace())

    metrics = []

    @capture_transaction_metrics(metrics)
    def _test():
        event_loop.run_until_complete(parent_task())

    _test()

    assert main_metric in metrics
    assert deferred_metric not in metrics
