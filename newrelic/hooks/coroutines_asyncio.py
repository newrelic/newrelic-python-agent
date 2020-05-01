from newrelic.common.object_wrapper import (
        wrap_out_function, wrap_function_wrapper)
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


def instrument_asyncio_events(module):
    wrap_function_wrapper(
        module,
        'BaseDefaultEventLoopPolicy.set_event_loop',
        wrap_create_task)
