import sys
import types
import time
import traceback

import newrelic.core.database_node

import newrelic.api.transaction
import newrelic.api.time_trace
import newrelic.api.object_wrapper

class DatabaseTrace(newrelic.api.time_trace.TimeTrace):

    node = newrelic.core.database_node.DatabaseNode

    def __init__(self, transaction, sql, dbapi=None,
                 connect_params=None, cursor_params=None,
                 execute_params=None):

        super(DatabaseTrace, self).__init__(transaction)

        if transaction:
            self.sql = transaction._intern_string(sql)
        else:
            self.sql = sql

        self.dbapi = dbapi

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.execute_params = execute_params

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(sql=self.sql)

    def finalize_data(self):
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
            # there is a chance we will need to do an explain plan.

            if (transaction_tracer.explain_enabled and
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
        return self.node(dbapi=self.dbapi, sql=self.sql,
                children=self.children, start_time=self.start_time,
                end_time=self.end_time, duration=self.duration,
                exclusive=self.exclusive, stack_trace=self.stack_trace,
                sql_format=self.sql_format, connect_params=self.connect_params,
                cursor_params=self.cursor_params,
                execute_params=self.execute_params)

    def terminal_node(self):
        return True

class DatabaseTraceWrapper(object):

    def __init__(self, wrapped, sql, dbapi=None):
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
        self._nr_dbapi = dbapi

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_sql,
                              self._nr_dbapi)

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

        with DatabaseTrace(transaction, sql, self._nr_dbapi):
            return self._nr_next_object(*args, **kwargs)

def database_trace(sql, dbapi=None):
    def decorator(wrapped):
        return DatabaseTraceWrapper(wrapped, sql, dbapi=None)
    return decorator

def wrap_database_trace(module, object_path, sql, dbapi=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            DatabaseTraceWrapper, (sql, dbapi))
