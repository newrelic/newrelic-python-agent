import inspect

from newrelic.common.object_wrapper import ObjectProxy


if hasattr(inspect, 'iscoroutinefunction'):
    def is_coroutine_function(wrapped):
        return (inspect.iscoroutinefunction(wrapped) or
                inspect.isgeneratorfunction(wrapped))
else:
    def is_coroutine_function(wrapped):
        return inspect.isgeneratorfunction(wrapped)


class TraceContext(object):
    def __init__(self, trace):
        self.trace = trace

    def __enter__(self):
        if not self.trace:
            return self

        if not self.trace.activated:
            self.trace.__enter__()

            # Transaction can be cleared by calling enter (such as when tracing
            # as a child of a terminal node)
            # In this case, we clear out the transaction and defer to the
            # wrapped function
            if not self.trace.transaction:
                self.trace = None
        else:
            # In the case that the function trace is already active, notify the
            # transaction that this coroutine is now the current node (for
            # automatic parenting)
            self.trace.transaction._push_current(self.trace)

        return self

    def __exit__(self, exc, value, tb):
        if not self.trace:
            return

        if exc in (StopIteration, GeneratorExit):
            self.trace.__exit__(None, None, None)
            self.trace = None
        elif exc:
            self.trace.__exit__(exc, value, tb)
            self.trace = None
        else:
            # Since the coroutine is returning control to the parent at this
            # point, we should notify the transaction that this coroutine is no
            # longer the current node for parenting purposes
            if self.trace.transaction.current_node is self.trace:
                self.trace.transaction._pop_current(self.trace)


class CoroutineTrace(ObjectProxy):
    def __init__(self, wrapped, trace):

        self._nr_trace_context = TraceContext(trace)

        # get the coroutine
        coro = wrapped()
        if hasattr(coro, '__iter__'):
            coro = iter(coro)

        # Wrap the coroutine
        super(CoroutineTrace, self).__init__(coro)

    def __iter__(self):
        return self

    def __await__(self):
        return self

    def __next__(self):
        return self.send(None)

    next = __next__

    def send(self, value):
        with self._nr_trace_context:
            return self.__wrapped__.send(value)

    def throw(self, *args, **kwargs):
        with self._nr_trace_context:
            return self.__wrapped__.throw(*args, **kwargs)

    def close(self):
        try:
            with self._nr_trace_context:
                result = self.__wrapped__.close()
        except:
            raise
        else:
            # If the trace hasn't been exited, then exit the trace
            if self._nr_trace_context.trace:
                self._nr_trace_context.trace.__exit__(None, None, None)
                self._nr_trace_context.trace = None
            return result


def return_value_fn(wrapped):
    if is_coroutine_function(wrapped):
        def return_value(trace, fn):
            return CoroutineTrace(fn, trace)
    else:
        def return_value(trace, fn):
            with trace:
                return fn()

    return return_value
