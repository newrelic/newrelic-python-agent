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

import functools
import gc
import sys
import time

import pytest
from testing_support.fixtures import capture_transaction_metrics, validate_tt_parenting
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.web_transaction import web_transaction

asyncio = pytest.importorskip("asyncio")
is_pypy = hasattr(sys, "pypy_version_info")


@pytest.mark.parametrize(
    "transaction,is_bg_task",
    [
        (functools.partial(background_task, name="simple_gen"), True),
        (functools.partial(web_transaction, name="simple_gen"), False),
    ],
)
def test_async_generator_timing(event_loop, transaction, is_bg_task):
    @transaction()
    async def simple_gen():
        time.sleep(0.1)
        yield
        time.sleep(0.1)

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics("simple_gen", background_task=is_bg_task)
    def _test_async_generator_timing():
        async def _test():
            async for _ in simple_gen():
                pass

        event_loop.run_until_complete(_test())

    _test_async_generator_timing()

    # Check that coroutines time the total call time (including pauses)
    metric_key = (f"{'Other' if is_bg_task else 'Web'}Transaction/Function/simple_gen", "")
    assert full_metrics[metric_key].total_call_time >= 0.2


class MyException(Exception):
    pass


@validate_transaction_metrics("test_async_generator_error", background_task=True)
@validate_transaction_errors(errors=["test_async_generator_transaction_proxy:MyException"])
def test_async_generator_error(event_loop):
    @background_task(name="test_async_generator_error")
    async def agen():
        yield

    async def _test():
        gen = agen()
        await gen.asend(None)
        await gen.athrow(MyException)

    with pytest.raises(MyException):
        event_loop.run_until_complete(_test())


@validate_transaction_metrics("test_async_generator_caught_exception", background_task=True)
@validate_transaction_errors(errors=[])
def test_async_generator_caught_exception(event_loop):
    @background_task(name="test_async_generator_caught_exception")
    async def agen():
        for _ in range(2):
            time.sleep(0.1)
            try:
                yield
            except ValueError:
                pass

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    def _test_async_generator_caught_exception():
        async def _test():
            gen = agen()
            # kickstart the generator (the try/except logic is inside the
            # generator)
            await gen.asend(None)
            await gen.athrow(ValueError)

            # consume the generator
            async for _ in gen:
                pass

        # The ValueError should not be reraised
        event_loop.run_until_complete(_test())

    _test_async_generator_caught_exception()

    metric_key = "OtherTransaction/Function/test_async_generator_caught_exception"
    assert full_metrics[(metric_key, "")].total_call_time >= 0.2


def test_async_generator_aclose_ends_transaction(event_loop):
    @background_task(name="test_async_generator_aclose_ends_transaction")
    async def agen():
        yield

    # Save a reference to the generator and run the validations before that
    # is garbage collected to avoid this test becoming a duplicate
    # of the test "test_incomplete_async_generator"
    gen = agen()

    @validate_transaction_metrics("test_async_generator_aclose_ends_transaction", background_task=True)
    def _test_async_generator_aclose_ends_transaction():
        async def _test():
            # kickstart the coroutine
            await gen.asend(None)

            # trace should be ended/recorded by close
            await gen.aclose()

            # We may call gen.close as many times as we want
            await gen.aclose()

        event_loop.run_until_complete(_test())

    _test_async_generator_aclose_ends_transaction()


@validate_transaction_metrics("test_asend_receives_a_value", background_task=True)
def test_asend_receives_a_value(event_loop):
    _received = []

    @background_task(name="test_asend_receives_a_value")
    async def agen():
        value = yield
        _received.append(value)
        yield value

    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        assert await gen.asend("foobar") == "foobar"
        assert _received[0] == "foobar"

        # finish consumption of the coroutine if necessary
        async for _ in gen:
            pass

    event_loop.run_until_complete(_test())


@validate_transaction_metrics("test_athrow_yields_a_value", background_task=True)
def test_athrow_yields_a_value(event_loop):
    @background_task(name="test_athrow_yields_a_value")
    async def agen():
        for _ in range(2):
            try:
                yield
            except MyException:
                yield "foobar"

    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        assert await gen.athrow(MyException) == "foobar"

        # finish consumption of the coroutine if necessary
        async for _ in gen:
            pass

    event_loop.run_until_complete(_test())


@validate_transaction_metrics("test_multiple_throws_yield_a_value", background_task=True)
def test_multiple_throws_yield_a_value(event_loop):
    @background_task(name="test_multiple_throws_yield_a_value")
    async def agen():
        value = None
        for _ in range(4):
            try:
                yield value
                value = "bar"
            except MyException:
                value = "foo"

    async def _test():
        gen = agen()

        # kickstart the coroutine
        assert await gen.asend(None) is None
        assert await gen.athrow(MyException) == "foo"
        assert await gen.athrow(MyException) == "foo"
        assert await gen.asend(None) == "bar"

        # finish consumption of the coroutine if necessary
        async for _ in gen:
            pass

    event_loop.run_until_complete(_test())


@validate_transaction_metrics("test_athrow_does_not_yield_a_value", background_task=True)
def test_athrow_does_not_yield_a_value(event_loop):
    @background_task(name="test_athrow_does_not_yield_a_value")
    async def agen():
        for _ in range(2):
            try:
                yield
            except MyException:
                return

    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        # async generator will raise StopAsyncIteration
        with pytest.raises(StopAsyncIteration):
            await gen.athrow(MyException)

    event_loop.run_until_complete(_test())


@validate_transaction_metrics("test_catching_generator_exit_causes_runtime_error", background_task=True)
def test_catching_generator_exit_causes_runtime_error(event_loop):
    @background_task(name="test_catching_generator_exit_causes_runtime_error")
    async def agen():
        try:
            yield
        except GeneratorExit:
            yield

    async def _test():
        gen = agen()

        # kickstart the coroutine (we're inside the try now)
        await gen.asend(None)

        # Generators cannot catch generator exit exceptions (which are injected by
        # close). This will result in a runtime error.
        with pytest.raises(RuntimeError):
            await gen.aclose()

    event_loop.run_until_complete(_test())


@validate_transaction_metrics("test_async_generator_time_excludes_creation_time", background_task=True)
def test_async_generator_time_excludes_creation_time(event_loop):
    @background_task(name="test_async_generator_time_excludes_creation_time")
    async def agen():
        yield

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    def _test_async_generator_time_excludes_creation_time():
        async def _test():
            gen = agen()
            time.sleep(0.1)
            async for _ in gen:
                pass

        event_loop.run_until_complete(_test())

    _test_async_generator_time_excludes_creation_time()

    # check that the trace does not include the time between creation and
    # consumption
    metric_key = "OtherTransaction/Function/test_async_generator_time_excludes_creation_time"
    assert full_metrics[(metric_key, "")].total_call_time < 0.1


@validate_transaction_metrics("test_complete_async_generator", background_task=True)
def test_complete_async_generator(event_loop):
    @background_task(name="test_complete_async_generator")
    async def agen():
        for i in range(5):
            yield i

    async def _test():
        gen = agen()
        assert [x async for x in gen] == list(range(5))

    event_loop.run_until_complete(_test())


def test_incomplete_async_generator(event_loop):
    @background_task(name="test_incomplete_async_generator")
    async def agen():
        for _ in range(5):
            yield

    @validate_transaction_metrics("test_incomplete_async_generator", background_task=True)
    def _test_incomplete_async_generator():
        async def _test():
            c = agen()

            async for _ in c:
                break

            # This test differs from the test for async_proxy in that the generator
            # going out of scope does not immediately close the trace. Instead, it's
            # the transaction ending that closes the trace. No need to call gc.collect().

            if is_pypy:
                # pypy is not guaranteed to delete the coroutine when it goes out
                # of scope. This code "helps" pypy along. The test above is really
                # just to verify that incomplete coroutines will "eventually" be
                # cleaned up. In pypy, unfortunately that means it may not be
                # reported all the time. A customer would be expected to call gc
                # directly; however, they already have to handle this case since
                # incomplete generators are well documented as having problems with
                # pypy's gc.

                # See:
                # http://doc.pypy.org/en/latest/cpython_differences.html#differences-related-to-garbage-collection-strategies
                # https://bitbucket.org/pypy/pypy/issues/736

                del c
                gc.collect()

        event_loop.run_until_complete(_test())

    _test_incomplete_async_generator()
