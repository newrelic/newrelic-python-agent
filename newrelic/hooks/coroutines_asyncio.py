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

from newrelic.common.object_wrapper import wrap_function_wrapper, wrap_out_function
from newrelic.core.trace_cache import trace_cache


def remove_from_cache_callback(task):
    cache = trace_cache()
    cache.task_stop(task)


def wrap_create_task(task):
    trace_cache().task_start(task)
    task.add_done_callback(remove_from_cache_callback)
    return task


def _instrument_event_loop(loop):
    if loop and hasattr(loop, "create_task") and not hasattr(loop.create_task, "__wrapped__"):
        wrap_out_function(loop, "create_task", wrap_create_task)


def _bind_set_event_loop(loop, *args, **kwargs):
    return loop


def wrap_set_event_loop(wrapped, instance, args, kwargs):
    loop = _bind_set_event_loop(*args, **kwargs)

    _instrument_event_loop(loop)

    return wrapped(*args, **kwargs)


def wrap__lazy_init(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    # This logic can be used for uvloop, but should
    # work for any valid custom loop factory.

    # A custom loop_factory will be used to create
    # a new event loop instance.  It will then run
    # the main() coroutine on this event loop.  Once
    # this coroutine is complete, the event loop will
    # be stopped and closed.

    # The new loop that is created and set as the
    # running loop of the duration of the run() call.
    # When the coroutine starts, it runs in the context
    # that was active when run() was called.  Any tasks
    # created within this coroutine on this new event
    # loop will inherit that context.

    # Note: The loop created by loop_factory is never
    # set as the global current loop for the thread,
    # even while it is running.
    loop = instance._loop
    _instrument_event_loop(loop)

    return result


def instrument_asyncio_base_events(module):
    wrap_out_function(module, "BaseEventLoop.create_task", wrap_create_task)


def instrument_asyncio_events(module):
    if hasattr(module, "_BaseDefaultEventLoopPolicy"):  # Python >= 3.14
        wrap_function_wrapper(module, "_BaseDefaultEventLoopPolicy.set_event_loop", wrap_set_event_loop)
    elif hasattr(module, "BaseDefaultEventLoopPolicy"):  # Python <= 3.13
        wrap_function_wrapper(module, "BaseDefaultEventLoopPolicy.set_event_loop", wrap_set_event_loop)


# For Python >= 3.11
def instrument_asyncio_runners(module):
    if hasattr(module, "Runner") and hasattr(module.Runner, "_lazy_init"):
        wrap_function_wrapper(module, "Runner._lazy_init", wrap__lazy_init)
