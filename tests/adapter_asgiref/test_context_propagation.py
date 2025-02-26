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

from asgiref.sync import async_to_sync, sync_to_async
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.transaction import current_transaction


@sync_to_async
@function_trace()
def sync_func():
    assert current_transaction()
    return 1


@validate_transaction_metrics(
    "test_context_propagation:test_sync_to_async_context_propagation",
    scoped_metrics=[("Function/test_context_propagation:sync_func", 1)],
    rollup_metrics=[("Function/test_context_propagation:sync_func", 1)],
    background_task=True,
)
@background_task()
def test_sync_to_async_context_propagation(loop):
    async def _test():
        return_val = await sync_func()
        assert return_val == 1, "Sync function failed to return"

    loop.run_until_complete(_test())


@async_to_sync
@function_trace()
async def async_func():
    assert current_transaction()
    return 1


@validate_transaction_metrics(
    "test_context_propagation:test_async_to_sync_context_propagation",
    scoped_metrics=[("Function/test_context_propagation:async_func", 1)],
    rollup_metrics=[("Function/test_context_propagation:async_func", 1)],
    background_task=True,
)
@background_task()
def test_async_to_sync_context_propagation():
    return_val = async_func()
    assert return_val == 1, "Async function failed to return"
