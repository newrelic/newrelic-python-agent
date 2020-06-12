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

from newrelic.common.object_wrapper import wrap_out_function
from newrelic.api.time_trace import current_trace
from newrelic.core.trace_cache import trace_cache


def remove_from_cache(task):
    cache = trace_cache()
    cache._cache.pop(id(task), None)


def propagate_task_context(task):
    trace = current_trace()
    if trace:
        cache = trace_cache()
        cache._cache[id(task)] = trace
        task.add_done_callback(remove_from_cache)

    return task


def instrument_asyncio_base_events(module):
    wrap_out_function(
        module,
        'BaseEventLoop.create_task',
        propagate_task_context)
