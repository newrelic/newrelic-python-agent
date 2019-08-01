import functools

from newrelic.common.async_wrapper import async_wrapper
from newrelic.api.time_trace import TimeTrace, current_trace
from newrelic.core.memcache_node import MemcacheNode
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object


class MemcacheTrace(TimeTrace):

    def __init__(self, command, **kwargs):
        parent = None
        if kwargs:
            if len(kwargs) > 1:
                raise TypeError("Invalid keyword arguments:", kwargs)
            parent = kwargs['parent']
        super(MemcacheTrace, self).__init__(parent)

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
                guid=self.guid,
                agent_attributes=self.agent_attributes)


def MemcacheTraceWrapper(wrapped, command):

    def _nr_wrapper_memcache_trace_(wrapped, instance, args, kwargs):
        parent = current_trace()

        if parent is None:
            return wrapped(*args, **kwargs)

        if callable(command):
            if instance is not None:
                _command = command(instance, *args, **kwargs)
            else:
                _command = command(*args, **kwargs)
        else:
            _command = command

        trace = MemcacheTrace(_command, parent=parent)

        wrapper = async_wrapper(wrapped)
        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_wrapper_memcache_trace_)


def memcache_trace(command):
    return functools.partial(MemcacheTraceWrapper, command=command)


def wrap_memcache_trace(module, object_path, command):
    wrap_object(module, object_path, MemcacheTraceWrapper, (command,))
