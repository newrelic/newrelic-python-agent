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
import sys
import time

import pytest
from testing_support.fixtures import capture_transaction_metrics, validate_tt_parenting
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.function_trace import function_trace
from newrelic.api.graphql_trace import graphql_operation_trace, graphql_resolver_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace

asyncio = pytest.importorskip("asyncio")


@pytest.mark.parametrize(
    "trace,metric",
    [
        (functools.partial(function_trace, name="simple_gen"), "Function/simple_gen"),
        (functools.partial(external_trace, library="lib", url="http://foo.com"), "External/foo.com/lib/"),
        (functools.partial(database_trace, "select * from foo"), "Datastore/statement/None/foo/select"),
        (functools.partial(datastore_trace, "lib", "foo", "bar"), "Datastore/statement/lib/foo/bar"),
        (functools.partial(message_trace, "lib", "op", "typ", "name"), "MessageBroker/lib/typ/op/Named/name"),
        (functools.partial(memcache_trace, "cmd"), "Memcache/cmd"),
        (functools.partial(graphql_operation_trace), "GraphQL/operation/GraphQL/<unknown>/<anonymous>/<unknown>"),
        (functools.partial(graphql_resolver_trace), "GraphQL/resolve/GraphQL/<unknown>"),
    ],
)
def test_async_generator_timing(event_loop, trace, metric):
    @trace()
    async def simple_gen():
        time.sleep(0.1)
        yield
        time.sleep(0.1)

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics(
        "test_async_generator_timing", background_task=True, scoped_metrics=[(metric, 1)], rollup_metrics=[(metric, 1)]
    )
    @background_task(name="test_async_generator_timing")
    def _test_async_generator_timing():
        async def _test():
            async for _ in simple_gen():
                pass

        event_loop.run_until_complete(_test())

    _test_async_generator_timing()

    # Check that coroutines time the total call time (including pauses)
    metric_key = (metric, "")
    assert full_metrics[metric_key].total_call_time >= 0.2


class MyException(Exception):
    pass


@validate_transaction_metrics(
    "test_async_generator_error",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
@validate_transaction_errors(errors=["_test_async_generator_trace:MyException"])
def test_async_generator_error(event_loop):
    @function_trace(name="agen")
    async def agen():
        yield

    @background_task(name="test_async_generator_error")
    async def _test():
        gen = agen()
        await gen.asend(None)
        await gen.athrow(MyException)

    with pytest.raises(MyException):
        event_loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_async_generator_caught_exception",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
@validate_transaction_errors(errors=[])
def test_async_generator_caught_exception(event_loop):
    @function_trace(name="agen")
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
    @background_task(name="test_async_generator_caught_exception")
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

    assert full_metrics[("Function/agen", "")].total_call_time >= 0.2


@validate_transaction_metrics(
    "test_async_generator_handles_terminal_nodes",
    background_task=True,
    scoped_metrics=[("Function/parent", 1), ("Function/agen", None)],
    rollup_metrics=[("Function/parent", 1), ("Function/agen", None)],
)
def test_async_generator_handles_terminal_nodes(event_loop):
    # sometimes coroutines can be called underneath terminal nodes
    # In this case, the trace shouldn't actually be created and we also
    # shouldn't get any errors

    @function_trace(name="agen")
    async def agen():
        yield
        time.sleep(0.1)

    @function_trace(name="parent", terminal=True)
    async def parent():
        # parent calls child
        async for _ in agen():
            pass

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name="test_async_generator_handles_terminal_nodes")
    def _test_async_generator_handles_terminal_nodes():
        async def _test():
            await parent()

        event_loop.run_until_complete(_test())

    _test_async_generator_handles_terminal_nodes()

    metric_key = ("Function/parent", "")
    assert full_metrics[metric_key].total_exclusive_call_time >= 0.1


@validate_transaction_metrics(
    "test_async_generator_close_ends_trace",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_async_generator_close_ends_trace(event_loop):
    @function_trace(name="agen")
    async def agen():
        yield

    @background_task(name="test_async_generator_close_ends_trace")
    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        # trace should be ended/recorded by close
        await gen.aclose()

        # We may call gen.close as many times as we want
        await gen.aclose()

    event_loop.run_until_complete(_test())


@validate_tt_parenting(("TransactionNode", [("FunctionNode", [("FunctionNode", [])])]))
@validate_transaction_metrics(
    "test_async_generator_parents",
    background_task=True,
    scoped_metrics=[("Function/child", 1), ("Function/parent", 1)],
    rollup_metrics=[("Function/child", 1), ("Function/parent", 1)],
)
def test_async_generator_parents(event_loop):
    @function_trace(name="child")
    async def child():
        yield
        time.sleep(0.1)
        yield

    @function_trace(name="parent")
    async def parent():
        time.sleep(0.1)
        yield
        async for _ in child():
            pass

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name="test_async_generator_parents")
    def _test_async_generator_parents():
        async def _test():
            async for _ in parent():
                pass

        event_loop.run_until_complete(_test())

    _test_async_generator_parents()

    # Check that the child time is subtracted from the parent time (parenting
    # relationship is correctly established)
    key = ("Function/parent", "")
    assert full_metrics[key].total_exclusive_call_time < 0.2


@validate_transaction_metrics(
    "test_asend_receives_a_value",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_asend_receives_a_value(event_loop):
    _received = []

    @function_trace(name="agen")
    async def agen():
        value = yield
        _received.append(value)
        yield value

    @background_task(name="test_asend_receives_a_value")
    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        assert await gen.asend("foobar") == "foobar"
        assert _received and _received[0] == "foobar"

        # finish consumption of the coroutine if necessary
        async for _ in gen:
            pass

    event_loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_athrow_yields_a_value",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_athrow_yields_a_value(event_loop):
    @function_trace(name="agen")
    async def agen():
        for _ in range(2):
            try:
                yield
            except MyException:
                yield "foobar"

    @background_task(name="test_athrow_yields_a_value")
    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        assert await gen.athrow(MyException) == "foobar"

        # finish consumption of the coroutine if necessary
        async for _ in gen:
            pass

    event_loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_multiple_throws_yield_a_value",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_multiple_throws_yield_a_value(event_loop):
    @function_trace(name="agen")
    async def agen():
        value = None
        for _ in range(4):
            try:
                yield value
                value = "bar"
            except MyException:
                value = "foo"

    @background_task(name="test_multiple_throws_yield_a_value")
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


@validate_transaction_metrics(
    "test_athrow_does_not_yield_a_value",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_athrow_does_not_yield_a_value(event_loop):
    @function_trace(name="agen")
    async def agen():
        for _ in range(2):
            try:
                yield
            except MyException:
                return

    @background_task(name="test_athrow_does_not_yield_a_value")
    async def _test():
        gen = agen()

        # kickstart the coroutine
        await gen.asend(None)

        # async generator will raise StopAsyncIteration
        with pytest.raises(StopAsyncIteration):
            await gen.athrow(MyException)

    event_loop.run_until_complete(_test())


@pytest.mark.parametrize(
    "trace",
    [
        function_trace(name="simple_gen"),
        external_trace(library="lib", url="http://foo.com"),
        database_trace("select * from foo"),
        datastore_trace("lib", "foo", "bar"),
        message_trace("lib", "op", "typ", "name"),
        memcache_trace("cmd"),
    ],
)
def test_async_generator_functions_outside_of_transaction(event_loop, trace):
    @trace
    async def agen():
        for _ in range(2):
            yield "foo"

    async def _test():
        assert [_ async for _ in agen()] == ["foo", "foo"]

    event_loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_catching_generator_exit_causes_runtime_error",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_catching_generator_exit_causes_runtime_error(event_loop):
    @function_trace(name="agen")
    async def agen():
        try:
            yield
        except GeneratorExit:
            yield

    @background_task(name="test_catching_generator_exit_causes_runtime_error")
    async def _test():
        gen = agen()

        # kickstart the coroutine (we're inside the try now)
        await gen.asend(None)

        # Generators cannot catch generator exit exceptions (which are injected by
        # close). This will result in a runtime error.
        with pytest.raises(RuntimeError):
            await gen.aclose()

    event_loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_async_generator_time_excludes_creation_time",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
def test_async_generator_time_excludes_creation_time(event_loop):
    @function_trace(name="agen")
    async def agen():
        yield

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @background_task(name="test_async_generator_time_excludes_creation_time")
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
    assert full_metrics[("Function/agen", "")].total_call_time < 0.1


@validate_transaction_metrics(
    "test_complete_async_generator",
    background_task=True,
    scoped_metrics=[("Function/agen", 1)],
    rollup_metrics=[("Function/agen", 1)],
)
@background_task(name="test_complete_async_generator")
def test_complete_async_generator(event_loop):
    @function_trace(name="agen")
    async def agen():
        for i in range(5):
            yield i

    async def _test():
        gen = agen()
        assert [x async for x in gen] == [x for x in range(5)]

    event_loop.run_until_complete(_test())


@pytest.mark.parametrize("nr_transaction", [True, False])
def test_incomplete_async_generator(event_loop, nr_transaction):
    @function_trace(name="agen")
    async def agen():
        for _ in range(5):
            yield

    def _test_incomplete_async_generator():
        async def _test():
            c = agen()

            async for _ in c:
                break

        if nr_transaction:
            _test = background_task(name="test_incomplete_async_generator")(_test)

        event_loop.run_until_complete(_test())

    if nr_transaction:
        _test_incomplete_async_generator = validate_transaction_metrics(
            "test_incomplete_async_generator",
            background_task=True,
            scoped_metrics=[("Function/agen", 1)],
            rollup_metrics=[("Function/agen", 1)],
        )(_test_incomplete_async_generator)

    _test_incomplete_async_generator()


def test_incomplete_async_generator_transaction_exited(event_loop):
    @function_trace(name="agen")
    async def agen():
        for _ in range(5):
            yield

    @validate_transaction_metrics(
        "test_incomplete_async_generator",
        background_task=True,
        scoped_metrics=[("Function/agen", 1)],
        rollup_metrics=[("Function/agen", 1)],
    )
    def _test_incomplete_async_generator():
        c = agen()

        @background_task(name="test_incomplete_async_generator")
        async def _test():
            async for _ in c:
                break

        event_loop.run_until_complete(_test())

        # Remove generator after transaction completes
        del c

    _test_incomplete_async_generator()
