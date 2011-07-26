import _newrelic

import newrelic.core.object_wrapper
import newrelic.core.trace_wrapper

__all__ = [ 'FunctionTraceWrapper', 'function_trace', 'wrap_function_trace' ]

class FunctionTraceWrapper(newrelic.core.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, name=None, scope=None, interesting=True):
        newrelic.core.trace_wrapper.TraceWrapper.__init__(self,
                _newrelic.FunctionTrace, wrapped, name, scope, interesting)

    def tracer_args(self, args, kwargs):
        (name, scope, interesting) = self._nr_tracer_args

        if name is None:
            name = _newrelic.callable_name(self._nr_next_object)
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
    newrelic.core.object_wrapper.wrap_object(module, object_path,
            FunctionTraceWrapper, (name, scope, interesting))
