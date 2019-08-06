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
