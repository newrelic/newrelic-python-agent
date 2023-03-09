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

from newrelic.common.object_wrapper import (
    wrap_function_wrapper,
    wrap_in_function,
    wrap_out_function,
)
from newrelic.core.trace_cache import trace_cache


def remove_from_cache(task):
    cache = trace_cache()
    cache.task_stop(task)


def propagate_task_context(task):
    trace_cache().task_start(task)
    task.add_done_callback(remove_from_cache)
    return task


def propagate_context_to_thread(instance, thread_pool, function, *args, **kwargs):
    current_trace = trace_cache().current_trace()
    if not current_trace:
        return ((instance, thread_pool, function, *args), kwargs)

    def inject_context_to_thread_wrapper(*args, **kwargs):
        try:
            trace_cache()[trace_cache().current_thread_id()] = current_trace
            return function(*args, **kwargs)
        finally:
            trace_cache().pop(trace_cache().current_thread_id(), None)

    return ((instance, thread_pool, inject_context_to_thread_wrapper, *args), kwargs)


def _bind_loop(loop, *args, **kwargs):
    return loop


def wrap_create_task(wrapped, instance, args, kwargs):
    loop = _bind_loop(*args, **kwargs)

    if loop and not hasattr(loop.create_task, '__wrapped__'):
        wrap_out_function(
            loop,
            'create_task',
            propagate_task_context)

    return wrapped(*args, **kwargs)


def instrument_asyncio_base_events(module):
    wrap_out_function(
        module,
        'BaseEventLoop.create_task',
        propagate_task_context)

    wrap_in_function(
        module,
        'BaseEventLoop.run_in_executor',
        propagate_context_to_thread)

    wrap_in_function(
        "uvloop",
        'Loop.run_in_executor',
        propagate_context_to_thread)


def instrument_asyncio_events(module):
    wrap_function_wrapper(
        module,
        'BaseDefaultEventLoopPolicy.set_event_loop',
        wrap_create_task)
