from __future__ import with_statement

import sys
import types
import inspect
import time
import traceback

import newrelic.core.database_node

import newrelic.api.transaction
import newrelic.api.time_trace
import newrelic.api.object_wrapper

class DatabaseTrace(newrelic.api.time_trace.TimeTrace):

    node = newrelic.core.database_node.DatabaseNode

    def __init__(self, transaction, sql, dbapi=None):
        super(DatabaseTrace, self).__init__(transaction)

        self.sql = sql
        self.dbapi = dbapi

        self.connect_params = None

    def finalize_data(self):
        self.stack_trace = None

        settings = self.transaction.settings
        transaction_tracer = settings.transaction_tracer

        if transaction_tracer.enabled and settings.collect_traces:
            if self.duration >= transaction_tracer.stack_trace_threshold:
                self.stack_trace = traceback.format_stack()

        self.sql_format = transaction_tracer.record_sql

    def create_node(self):
        return self.node(dbapi=self.dbapi, sql=self.sql,
                children=self.children, connect_params=self.connect_params,
                start_time=self.start_time, end_time=self.end_time,
                duration=self.duration, exclusive=self.exclusive,
                stack_trace=self.stack_trace, sql_format=self.sql_format)

    def terminal_node(self):
        return True

class DatabaseTraceWrapper(object):

    def __init__(self, wrapped, sql, dbapi=None):
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
        self._nr_dbapi = dbapi

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_sql,
                              self._nr_dbapi)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if not isinstance(self._nr_sql, basestring):
            if self._nr_instance and inspect.ismethod(self._nr_next_object):
                sql = self._nr_sql(self._nr_instance, *args, **kwargs)
            else:
                sql = self._nr_sql(*args, **kwargs)
        else:
            sql = self._nr_sql

        with DatabaseTrace(transaction, sql, self._nr_dbapi):
            return self._nr_next_object(*args, **kwargs)

def database_trace(sql, dbapi=None):
    def decorator(wrapped):
        return DatabaseTraceWrapper(wrapped, sql, dbapi=None)
    return decorator

def wrap_database_trace(module, object_path, sql, dbapi=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            DatabaseTraceWrapper, (sql, dbapi))
