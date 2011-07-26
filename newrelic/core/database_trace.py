import _newrelic

import newrelic.core.object_wrapper
import newrelic.core.trace_wrapper

__all__ = [ 'DatabaseTraceWrapper', 'database_trace', 'wrap_database_trace' ]

class DatabaseTraceWrapper(newrelic.core.trace_wrapper.TraceWrapper):

    def __init__(self, wrapped, sql):
        newrelic.core.trace_wrapper.TraceWrapper.__init__(self,
                _newrelic.DatabaseTrace, wrapped, sql)

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
    newrelic.core.object_wrapper.wrap_object(module, object_path,
            DatabaseTraceWrapper, (sql,))
