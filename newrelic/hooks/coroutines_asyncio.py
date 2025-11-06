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

from newrelic.api.time_trace import current_trace
from newrelic.common.object_wrapper import wrap_function_wrapper, wrap_out_function
from newrelic.core.context import context_wrapper
from newrelic.core.trace_cache import trace_cache


def remove_from_cache(task):
    cache = trace_cache()
    cache.task_stop(task)


def propagate_task_context(task):
    trace_cache().task_start(task)
    task.add_done_callback(remove_from_cache)
    return task


def _bind_loop(loop, *args, **kwargs):
    return loop


def _instrument_event_loop(wrapped, instance, args, kwargs):
    """Instrument the newly set event loop if the methods aren't already wrapped."""
    loop = _bind_loop(*args, **kwargs)

    if loop and not hasattr(loop.create_task, "__wrapped__"):
        wrap_out_function(loop, "create_task", propagate_task_context)
    if loop and hasattr(loop, "run_in_executor") and not hasattr(loop.run_in_executor, "__wrapped__"):
        wrap_function_wrapper(loop, "run_in_executor", wrap_run_in_executor)

    return wrapped(*args, **kwargs)


def _bind_run_in_executor(executor, func, *args):
    return executor, func, args


def wrap_run_in_executor(wrapped, instance, args, kwargs):
    """Instrument run_in_executor to propagate trace context automatically."""
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    # Replace the original target function with a wrapped version that propagates trace context.
    executor, func, args = _bind_run_in_executor(*args, **kwargs)
    wrapped_func = context_wrapper(func, trace=trace, strict=False)
    return wrapped(executor, wrapped_func, *args)


def instrument_asyncio_base_events(module):
    wrap_out_function(module, "BaseEventLoop.create_task", propagate_task_context)
    wrap_function_wrapper(module, "BaseEventLoop.run_in_executor", wrap_run_in_executor)


def instrument_asyncio_events(module):
    if hasattr(module, "_BaseDefaultEventLoopPolicy"):  # Python >= 3.14
        wrap_function_wrapper(module, "_BaseDefaultEventLoopPolicy.set_event_loop", _instrument_event_loop)
    else:  # Python <= 3.13
        wrap_function_wrapper(module, "BaseDefaultEventLoopPolicy.set_event_loop", _instrument_event_loop)
