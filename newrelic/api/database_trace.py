import os
import sys
import types
import inspect

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class DatabaseTrace(object):

    def __init__(self, transaction, sql):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc, value, tb):
        pass

if _agent_mode not in ('julunggul',):
    import _newrelic
    DatabaseTrace = _newrelic.DatabaseTrace

class DatabaseTraceWrapper(object):

    def __init__(self, wrapped, sql):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_sql = sql

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_sql)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if not isinstance(self._nr_sql, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                sql = self._nr_sql(*((self._nr_instance,)+args), **kwargs)
            else:
                sql = self._nr_sql(*args, **kwargs)
        else:
            sql = self._nr_sql

        try:
            success = True
            manager = DatabaseTrace(transaction, sql)
            manager.__enter__()
            try:
                return self._nr_next_object(*args, **kwargs)
            except:
                success = False
                if not manager.__exit__(*sys.exc_info()):
                    raise
        finally:
            if success:
                manager.__exit__(None, None, None)

def database_trace(sql):
    def decorator(wrapped):
        return DatabaseTraceWrapper(wrapped, sql)
    return decorator

def wrap_database_trace(module, object_path, sql):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            DatabaseTraceWrapper, (sql,))

if not _agent_mode in ('ungud', 'julunggul'):
    import _newrelic
    DatabaseTraceWrapper = _newrelic.DatabaseTraceWrapper
    database_trace = _newrelic.database_trace
    wrap_database_trace = _newrelic.wrap_database_trace
