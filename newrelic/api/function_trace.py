import os

import _newrelic

import newrelic.api.object_wrapper
import newrelic.api.trace_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

FunctionTrace = _newrelic.FunctionTrace

class FunctionTraceWrapper(newrelic.api.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, name=None, scope=None, interesting=True):
        newrelic.api.trace_wrapper.TraceWrapper.__init__(self,
                FunctionTrace, wrapped, name, scope, interesting)

    def tracer_args(self, args, kwargs):
        (name, scope, interesting) = self._nr_tracer_args

        if name is None:
            name = newrelic.api.object_wrapper.callable_name(
                    self._nr_next_object)
        elif not isinstance(name, basestring):
            name = name(*args, **kwargs)
        if scope is not None and not isinstance(scope, basestring):
            scope = scope(*args, **kwargs)

        return (name, scope, interesting)

def function_trace(name=None, scope=None, interesting=True):
    def decorator(wrapped):
        return FunctionTraceWrapper(wrapped, name, scope, interesting)
    return decorator

def wrap_function_trace(module, object_path, name=None, scope=None,
        interesting=True):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            FunctionTraceWrapper, (name, scope, interesting))

if not _agent_mode in ('ungud', 'julunggul'):
    FunctionTraceWrapper = _newrelic.FunctionTraceWrapper
    function_trace = _newrelic.function_trace
    wrap_function_trace = _newrelic.wrap_function_trace
