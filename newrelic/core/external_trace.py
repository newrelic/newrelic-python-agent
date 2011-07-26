import _newrelic

import newrelic.core.object_wrapper
import newrelic.core.trace_wrapper

__all__ = [ 'ExternalTraceWrapper', 'external_trace', 'wrap_external_trace' ]

class ExternalTraceWrapper(newrelic.core.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, library, url):
        newrelic.core.trace_wrapper.TraceWrapper.__init__(self,
                _newrelic.ExternalTrace, wrapped, library, url)

    def tracer_args(self, args, kwargs):
        (library, url) = self._nr_tracer_args

        if not isinstance(url, basestring):
            url = url(*args, **kwargs)

        return (library, url)

def external_trace(library, url):
    def decorator(wrapped):
        return ExternalTraceWrapper(wrapped, library, url)
    return decorator

def wrap_external_trace(module, object_path, library, url):
    newrelic.core.object_wrapper.wrap_object(module, object_path,
            ExternalTraceWrapper, (library, url))
