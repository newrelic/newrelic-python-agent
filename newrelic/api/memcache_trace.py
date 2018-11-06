import functools

from newrelic.api.coroutine_trace import return_value_fn
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.core.memcache_node import MemcacheNode
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object


class MemcacheTrace(TimeTrace):

    def __init__(self, transaction, command):
        super(MemcacheTrace, self).__init__(transaction)

        self.command = command

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                command=self.command))

    def terminal_node(self):
        return True

    def create_node(self):
        return MemcacheNode(
                command=self.command,
                children=self.children,
                start_time=self.start_time,
                end_time=self.end_time,
                duration=self.duration,
                exclusive=self.exclusive,
                is_async=self.is_async,
                guid=self.guid)


def MemcacheTraceWrapper(wrapped, command):

    return_value = return_value_fn(wrapped)

    def _nr_wrapper_memcache_trace_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(command):
            if instance is not None:
                _command = command(instance, *args, **kwargs)
            else:
                _command = command(*args, **kwargs)
        else:
            _command = command

        trace = MemcacheTrace(transaction, _command)
        return return_value(trace, lambda: wrapped(*args, **kwargs))

    return FunctionWrapper(wrapped, _nr_wrapper_memcache_trace_)


def memcache_trace(command):
    return functools.partial(MemcacheTraceWrapper, command=command)


def wrap_memcache_trace(module, object_path, command):
    wrap_object(module, object_path, MemcacheTraceWrapper, (command,))
