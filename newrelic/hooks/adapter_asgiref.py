from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.trace_cache import trace_cache
from newrelic.core.context import context_wrapper_async, ContextOf


def _bind_thread_handler(loop, source_task, *args, **kwargs):
    return source_task


def thread_handler_wrapper(wrapped, instance, args, kwargs):
    task = _bind_thread_handler(*args, **kwargs)
    with ContextOf(id(task)):
        return wrapped(*args, **kwargs)


def main_wrap_wrapper(wrapped, instance, args, kwargs):
    awaitable = wrapped(*args, **kwargs)
    return context_wrapper_async(awaitable, trace_cache().current_thread_id())


def instrument_asgiref_sync(module):
    wrap_function_wrapper(module, 'SyncToAsync.thread_handler',
        thread_handler_wrapper)
    wrap_function_wrapper(module, 'AsyncToSync.main_wrap',
        main_wrap_wrapper)
