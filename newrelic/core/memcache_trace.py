import _newrelic

import newrelic.core.object_wrapper
import newrelic.core.trace_wrapper

__all__ = [ 'MemcacheTraceWrapper', 'memcache_trace', 'wrap_memcache_trace' ]

class MemcacheTraceWrapper(newrelic.core.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, command):
        newrelic.core.trace_wrapper.TraceWrapper.__init__(self,
                _newrelic.MemcacheTrace, wrapped, command)

    def tracer_args(self, args, kwargs):
        (command,) = self._nr_tracer_args

        if not isinstance(command, basestring):
            command = command(*args, **kwargs)

        return (command,)

def memcache_trace(command):
    def decorator(wrapped):
        return MemcacheTraceWrapper(wrapped, command)
    return decorator

def wrap_memcache_trace(module, object_path, command):
    newrelic.core.object_wrapper.wrap_object(module, object_path,
            MemcacheTraceWrapper, (command,))
