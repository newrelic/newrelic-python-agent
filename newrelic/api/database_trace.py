import sys
import types
import time
import traceback

import logging

import newrelic.core.database_node

import newrelic.api.transaction
import newrelic.api.time_trace
import newrelic.api.object_wrapper

_logger = logging.getLogger(__name__)

def register_database_client(dbapi2_module, database_name,
        quoting_style='single', explain_query=None, explain_stmts=[]):

    _logger.debug('Registering database client module %r where database '
            'is %r, quoting style is %r, explain query statement is %r and '
            'the SQL statements on which explain plans can be run are %r.',
            dbapi2_module, database_name, quoting_style, explain_query,
            explain_stmts)

    dbapi2_module._nr_database_name = database_name
    dbapi2_module._nr_quoting_style = quoting_style
    dbapi2_module._nr_explain_query = explain_query
    dbapi2_module._nr_explain_stmts = explain_stmts

class DatabaseTrace(newrelic.api.time_trace.TimeTrace):

    node = newrelic.core.database_node.DatabaseNode

    def __init__(self, transaction, sql, dbapi2_module=None,
                 connect_params=None, cursor_params=None,
                 execute_params=None):

        super(DatabaseTrace, self).__init__(transaction)

        if transaction:
            self.sql = transaction._intern_string(sql)
        else:
            self.sql = sql

        self.dbapi2_module = dbapi2_module

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.execute_params = execute_params

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(sql=self.sql)

    def finalize_data(self, exc=None, value=None, tb=None):
        self.stack_trace = None

        connect_params = None
        cursor_params = None
        execute_params = None

        settings = self.transaction.settings
        transaction_tracer = settings.transaction_tracer
        agent_limits = settings.agent_limits

        if transaction_tracer.enabled and settings.collect_traces:
            if self.duration >= transaction_tracer.stack_trace_threshold:
                if (self.transaction._stack_trace_count <
                        agent_limits.slow_sql_stack_trace):
                    self.stack_trace = [self.transaction._intern_string(x) for
                                        x in traceback.format_stack()]
                    self.transaction._stack_trace_count += 1


            # Only remember all the params for the calls if know
            # there is a chance we will need to do an explain
            # plan. We never allow an explain plan to be done if
            # an exception occurred in doing the query in case
            # doing the explain plan with the same inputs could
            # cause further problems.

            if (exc is None and transaction_tracer.explain_enabled and
                    self.duration >= transaction_tracer.explain_threshold):
                if (self.transaction._explain_plan_count <
                       agent_limits.sql_explain_plans):
                    connect_params = self.connect_params
                    cursor_params = self.cursor_params
                    execute_params = self.execute_params
                    self.transaction._explain_plan_count += 1

        self.sql_format = transaction_tracer.record_sql

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.execute_params = execute_params

    def create_node(self):
        return self.node(dbapi2_module=self.dbapi2_module, sql=self.sql,
                children=self.children, start_time=self.start_time,
                end_time=self.end_time, duration=self.duration,
                exclusive=self.exclusive, stack_trace=self.stack_trace,
                sql_format=self.sql_format, connect_params=self.connect_params,
                cursor_params=self.cursor_params,
                execute_params=self.execute_params)

    def terminal_node(self):
        return True

class DatabaseTraceWrapper(object):

    def __init__(self, wrapped, sql, dbapi2_module=None):
        if isinstance(wrapped, tuple):
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_sql = sql
        self._nr_dbapi2_module = dbapi2_module

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_sql,
                              self._nr_dbapi2_module)

    def __call__(self, *args, **kwargs):
        transaction = newrelic.api.transaction.current_transaction()
        if not transaction:
            return self._nr_next_object(*args, **kwargs)

        if callable(self._nr_sql):
            if self._nr_instance is not None:
                sql = self._nr_sql(self._nr_instance, *args, **kwargs)
            else:
                sql = self._nr_sql(*args, **kwargs)
        else:
            sql = self._nr_sql

        with DatabaseTrace(transaction, sql, self._nr_dbapi2_module):
            return self._nr_next_object(*args, **kwargs)

def database_trace(sql, dbapi2_module=None):
    def decorator(wrapped):
        return DatabaseTraceWrapper(wrapped, sql, dbapi2_module=None)
    return decorator

def wrap_database_trace(module, object_path, sql, dbapi2_module=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            DatabaseTraceWrapper, (sql, dbapi2_module))
