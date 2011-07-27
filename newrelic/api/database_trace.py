import os

import _newrelic

import newrelic.api.object_wrapper
import newrelic.api.trace_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

DatabaseTrace = _newrelic.DatabaseTrace

class DatabaseTraceWrapper(newrelic.api.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, sql):
        newrelic.api.trace_wrapper.TraceWrapper.__init__(self,
                DatabaseTrace, wrapped, sql)

    def tracer_args(self, args, kwargs):
        (sql,) = self._nr_tracer_args

        if not isinstance(sql, basestring):
            sql = sql(*args, **kwargs)

        return (sql,)

def database_trace(sql):
    def decorator(wrapped):
        return DatabaseTraceWrapper(wrapped, sql)
    return decorator

def wrap_database_trace(module, object_path, sql):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            DatabaseTraceWrapper, (sql,))

if not _agent_mode in ('ungud', 'julunggul'):
    DatabaseTraceWrapper = _newrelic.DatabaseTraceWrapper
    database_trace = _newrelic.database_trace
    wrap_database_trace = _newrelic.wrap_database_trace
