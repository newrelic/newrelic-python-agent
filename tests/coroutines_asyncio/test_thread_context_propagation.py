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

from testing_support.fixtures import override_generic_settings
from testing_support.validators.validate_function_not_called import validate_function_not_called
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace
from newrelic.core.config import global_settings
from newrelic.core.trace_cache import trace_cache


@background_task(name="test_thread_context_propagation")
async def _test(asyncio, nr_enabled=True):
    trace = current_trace()

    if nr_enabled:
        assert trace is not None
    else:
        assert trace is None

    await asyncio.to_thread(task1)


def task1():
    with FunctionTrace("task1"):
        pass


@validate_transaction_metrics(
    "test_thread_context_propagation", background_task=True, scoped_metrics=[("Function/task1", 1)]
)
def test_thread_context_propagation(event_loop, loop_policy):
    import asyncio

    asyncio.set_event_loop_policy(loop_policy)
    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    event_loop.set_exception_handler(handle_exception)

    # Calls run_in_executor on the current event loop
    event_loop.run_until_complete(_test(asyncio))

    # The agent should have removed all traces from the cache since
    # run_until_complete has terminated (all callbacks scheduled inside the
    # task have run)
    assert not trace_cache()

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions


@override_generic_settings(global_settings(), {"enabled": False})
@validate_function_not_called("newrelic.core.stats_engine", "StatsEngine.record_transaction")
def test_thread_nr_disabled(event_loop):
    import asyncio

    exceptions = []

    def handle_exception(loop, context):
        exceptions.append(context)

    event_loop.set_exception_handler(handle_exception)

    event_loop.run_until_complete(_test(asyncio, nr_enabled=False))

    # Assert that no exceptions have occurred
    assert not exceptions, exceptions
