from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.trace_cache import trace_cache


def _bind_thread_handler(loop, source_task, *args, **kwargs):
    return source_task


class ContextOf(object):
    def __init__(self, trace_cache_id):
        self.trace_cache = trace_cache()
        self.trace = self.trace_cache._cache.get(trace_cache_id)
        self.thread_id = None
        self.restore = None

    def __enter__(self):
        if self.trace:
            self.thread_id = self.trace_cache.current_thread_id()
            self.restore = self.trace_cache._cache.get(self.thread_id)
            self.trace_cache._cache[self.thread_id] = self.trace
        return self

    def __exit__(self, exc, value, tb):
        if self.restore:
            self.trace_cache._cache[self.thread_id] = self.restore


async def context_wrapper_async(awaitable, trace_cache_id):
    with ContextOf(trace_cache_id):
        return await awaitable


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
