import functools
import logging

from .time_trace import TimeTrace
from .transaction import current_transaction
from ..core.database_node import DatabaseNode
from ..core.stack_trace import current_stack
from ..common.object_wrapper import FunctionWrapper, wrap_object

_logger = logging.getLogger(__name__)

def register_database_client(dbapi2_module, database_name,
        quoting_style='single', explain_query=None, explain_stmts=[],
        instance_name=None):

    _logger.debug('Registering database client module %r where database '
            'is %r, quoting style is %r, explain query statement is %r and '
            'the SQL statements on which explain plans can be run are %r.',
            dbapi2_module, database_name, quoting_style, explain_query,
            explain_stmts)

    dbapi2_module._nr_database_name = database_name
    dbapi2_module._nr_quoting_style = quoting_style
    dbapi2_module._nr_explain_query = explain_query
    dbapi2_module._nr_explain_stmts = explain_stmts
    dbapi2_module._nr_instance_name = instance_name

class DatabaseTrace(TimeTrace):

    def __init__(self, transaction, sql, dbapi2_module=None,
                 connect_params=None, cursor_params=None,
                 sql_parameters=None, execute_params=None):

        super(DatabaseTrace, self).__init__(transaction)

        if transaction:
            self.sql = transaction._intern_string(sql)
        else:
            self.sql = sql

        self.dbapi2_module = dbapi2_module

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.sql_parameters = sql_parameters
        self.execute_params = execute_params

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                sql=self.sql, dbapi2_module=self.dbapi2_module))

    def finalize_data(self, transaction, exc=None, value=None, tb=None):
        self.stack_trace = None

        connect_params = None
        cursor_params = None
        sql_parameters = None
        execute_params = None

        settings = transaction.settings
        transaction_tracer = settings.transaction_tracer
        agent_limits = settings.agent_limits

        if (transaction_tracer.enabled and settings.collect_traces and
                transaction_tracer.record_sql != 'off'):
            if self.duration >= transaction_tracer.stack_trace_threshold:
                if (transaction._stack_trace_count <
                        agent_limits.slow_sql_stack_trace):
                    self.stack_trace = [transaction._intern_string(x) for
                                        x in current_stack(skip=2)]
                    transaction._stack_trace_count += 1


            # Only remember all the params for the calls if know
            # there is a chance we will need to do an explain
            # plan. We never allow an explain plan to be done if
            # an exception occurred in doing the query in case
            # doing the explain plan with the same inputs could
            # cause further problems.

            if (exc is None and transaction_tracer.explain_enabled and
                    self.duration >= transaction_tracer.explain_threshold and
                    self.connect_params is not None):
                if (transaction._explain_plan_count <
                       agent_limits.sql_explain_plans):
                    connect_params = self.connect_params
                    cursor_params = self.cursor_params
                    sql_parameters = self.sql_parameters
                    execute_params = self.execute_params
                    transaction._explain_plan_count += 1

        self.sql_format = transaction_tracer.record_sql

        self.connect_params = connect_params
        self.cursor_params = cursor_params
        self.sql_parameters = sql_parameters
        self.execute_params = execute_params

    def create_node(self):
        return DatabaseNode(dbapi2_module=self.dbapi2_module, sql=self.sql,
                children=self.children, start_time=self.start_time,
                end_time=self.end_time, duration=self.duration,
                exclusive=self.exclusive, stack_trace=self.stack_trace,
                sql_format=self.sql_format, connect_params=self.connect_params,
                cursor_params=self.cursor_params,
                sql_parameters=self.sql_parameters,
                execute_params=self.execute_params)

    def terminal_node(self):
        return True

def DatabaseTraceWrapper(wrapped, sql, dbapi2_module=None):

    def _nr_database_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(sql):
            if instance is not None:
                _sql = sql(instance, *args, **kwargs)
            else:
                _sql = sql(*args, **kwargs)
        else:
            _sql = sql

        with DatabaseTrace(transaction, _sql, dbapi2_module):
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, _nr_database_trace_wrapper_)

def database_trace(sql, dbapi2_module=None):
    return functools.partial(DatabaseTraceWrapper, sql=sql,
            dbapi2_module=dbapi2_module)

def wrap_database_trace(module, object_path, sql, dbapi2_module=None):
    wrap_object(module, object_path, DatabaseTraceWrapper,
            (sql, dbapi2_module))
