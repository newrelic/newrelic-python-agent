import os
import sys
import types
import inspect
import time
import traceback

import newrelic.core.transaction

import newrelic.api.transaction
import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class DatabaseTrace(object):

    def __init__(self, transaction, sql):
        self._transaction = transaction

        self._sql = sql

        self._enabled = False

        self._children = []

        self._start_time = 0.0
        self._end_time = 0.0

    def __enter__(self):
        if not self._transaction.active:
            return

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

        transaction_tracer = self._transaction.settings.transaction_tracer

        if duration >= transaction_tracer.stack_trace_threshold:
            stack_trace = traceback.format_stack()

        parent = self._transaction._node_stack[-1]

        node = newrelic.core.transaction.DatabaseNode(
                database_module=None,
                connect_params=None,
                sql=self._sql,
                children=self._children,
                start_time=self._start_time,
                end_time=self._end_time,
                duration=duration,
                exclusive=exclusive,
                stack_trace=stack_trace)

        parent._children.append(node)

        if duration >= transaction_tracer.stack_trace_threshold:
            self._transaction._slow_sql.append(node)

        self._children = []

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
        if not transaction or not transaction.active:
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
