import os

import _newrelic

import newrelic.api.object_wrapper
import newrelic.api.trace_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

MemcacheTrace = _newrelic.MemcacheTrace

class MemcacheTraceWrapper(newrelic.api.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, command):
        newrelic.api.trace_wrapper.TraceWrapper.__init__(self,
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
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            MemcacheTraceWrapper, (command,))

if not _agent_mode in ('ungud', 'julunggul'):
    MemcacheTraceWrapper = _newrelic.MemcacheTraceWrapper
    memcache_trace = _newrelic.memcache_trace
    wrap_memcache_trace = _newrelic.wrap_memcache_trace
