import os

import _newrelic

import newrelic.api.object_wrapper
import newrelic.api.trace_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

ExternalTrace = _newrelic.ExternalTrace

class ExternalTraceWrapper(newrelic.api.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, library, url):
        newrelic.api.trace_wrapper.TraceWrapper.__init__(self,
                ExternalTrace, wrapped, library, url)

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
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            ExternalTraceWrapper, (library, url))

if not _agent_mode in ('ungud', 'julunggul'):
    ExternalTraceWrapper = _newrelic.ExternalTraceWrapper
    external_trace = _newrelic.external_trace
    wrap_external_trace = _newrelic.wrap_external_trace
