import sys
import types
import inspect
import time
import traceback

import newrelic.core.database_node

import newrelic.api.transaction
import newrelic.api.object_wrapper

class DatabaseTrace(object):

    def __init__(self, transaction, sql, dbapi=None):
        self._transaction = transaction

        self._sql = sql
        self._dbapi = dbapi

        self._enabled = False

        self._children = []

        self._start_time = 0.0
        self._end_time = 0.0

    def __enter__(self):
        if not self._transaction:
            return self

        self._enabled = True

        self._start_time = time.time()

        self._transaction._node_stack.append(self)

        return self

    def __exit__(self, exc, value, tb):
        if not self._enabled:
            return

        self._end_time = time.time()

        duration = self._end_time - self._start_time

        exclusive = duration
        for child in self._children:
            exclusive -= child.duration
        exclusive = max(0, exclusive)

        root = self._transaction._node_stack.pop()
        assert(root == self)

        stack_trace = None

        settings = self._transaction.settings
        transaction_tracer = settings.transaction_tracer

        if transaction_tracer.enabled and settings.collect_traces:
            if duration >= transaction_tracer.stack_trace_threshold:
                stack_trace = traceback.format_stack()

        parent = self._transaction._node_stack[-1]

        settings = self._transaction.settings
        sql_format = settings.transaction_tracer.record_sql

        node = newrelic.core.database_node.DatabaseNode(
                dbapi=self._dbapi,
                connect_params=None,
                sql=self._sql,
                children=self._children,
                start_time=self._start_time,
                end_time=self._end_time,
                duration=duration,
                exclusive=exclusive,
                stack_trace=stack_trace,
                sql_format=sql_format)

        parent._children.append(node)

        if transaction_tracer.enabled and settings.collect_traces:
            if duration >= transaction_tracer.stack_trace_threshold:
                self._transaction._slow_sql.append(node)

        self._children = []

        self._transaction._build_count += 1
        self._transaction._build_time += (time.time() - self._end_time)

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
