from collections import namedtuple

import newrelic.core.trace_node

from newrelic.core.metric import TimeMetric
from newrelic.core.database_utils import sql_statement, explain_plan

_SlowSqlNode = namedtuple('_SlowSqlNode',
        ['duration', 'path', 'request_uri', 'sql', 'sql_format',
        'metric', 'dbapi2_module', 'stack_trace', 'connect_params',
        'cursor_params', 'sql_parameters', 'execute_params'])

class SlowSqlNode(_SlowSqlNode):

    def __new__(cls, *args, **kwargs):
        node = _SlowSqlNode.__new__(cls, *args, **kwargs)
        node.statement = sql_statement(node.sql, node.dbapi2_module)
        return node

    @property
    def formatted(self):
        return self.statement.formatted(self.sql_format)

    @property
    def identifier(self):
        return self.statement.identifier

_DatabaseNode = namedtuple('_DatabaseNode',
        ['dbapi2_module',  'sql', 'children', 'start_time', 'end_time',
        'duration', 'exclusive', 'stack_trace', 'sql_format',
        'connect_params', 'cursor_params', 'sql_parameters',
        'execute_params'])

class DatabaseNode(_DatabaseNode):

    def __new__(cls, *args, **kwargs):
        node = _DatabaseNode.__new__(cls, *args, **kwargs)
        node.statement = sql_statement(node.sql, node.dbapi2_module)
        return node

    @property
    def operation(self):
        return self.statement.operation

    @property
    def target(self):
        return self.statement.target

    @property
    def formatted(self):
        return self.statement.formatted(self.sql_format)

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.

        """

        yield TimeMetric(name='Database/all', scope='',
                duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield TimeMetric(name='Database/allWeb', scope='',
                    duration=self.duration, exclusive=self.exclusive)
        else:
            yield TimeMetric(name='Database/allOther', scope='',
                    duration=self.duration, exclusive=self.exclusive)

        # FIXME The follow is what PHP agent was doing, but it may
        # not sync up with what is now actually required. As example,
        # the 'show' operation in PHP agent doesn't generate a full
        # path with a table name, yet get_table() in SQL parser
        # does appear to generate one. Also, the SQL parser has
        # special cases for 'set', 'create' and 'call' as well.

        operation = self.operation

        if operation in ('select', 'update', 'insert', 'delete'):
            target = self.target

            if target:
                name = 'Database/%s/%s' % (self.target, operation)

                yield TimeMetric(name=name, scope='', duration=self.duration,
                        exclusive=self.exclusive)

                yield TimeMetric(name=name, scope=root.path,
                    duration=self.duration, exclusive=self.exclusive)

            name = 'Database/%s' % operation

            yield TimeMetric(name=name, scope='', duration=self.duration,
                    exclusive=self.exclusive)

        elif operation in ('show',):
            name = 'Database/%s' % operation

            yield TimeMetric(name=name, scope='', duration=self.duration,
                    exclusive=self.exclusive)

            yield TimeMetric(name=name, scope=root.path,
                    duration=self.duration, exclusive=self.exclusive)

        else:
            yield TimeMetric(name='Database/other', scope='',
                    duration=self.duration, exclusive=self.exclusive)

            yield TimeMetric(name='Database/other/sql', scope='',
                    duration=self.duration, exclusive=self.exclusive)

            yield TimeMetric(name='Database/other/sql', scope=root.path,
                    duration=self.duration, exclusive=self.exclusive)

    def slow_sql_node(self, stats, root):

        operation = self.operation

        if operation in ('select', 'update', 'insert', 'delete'):
            target = self.target
            if target:
                name = 'Database/%s/%s' % (target, operation)
            else:
                name = 'Database/%s' % operation
        elif operation in ('show',):
            name = 'Database/%s' % operation
        else:
            name = 'Database/other/sql'

        request_uri = ''
        if root.type == 'WebTransaction':
            request_uri = root.request_uri

        # Note that we do not limit the length of the SQL at this
        # point as we will need the whole SQL query when doing an
        # explain plan. Only limit the length when sending the
        # formatted SQL up to the data collector.

        return SlowSqlNode(duration=self.duration, path=root.path,
                request_uri=request_uri, sql=self.sql,
                sql_format=self.sql_format, metric=name,
                dbapi2_module=self.dbapi2_module,
                stack_trace=self.stack_trace,
                connect_params=self.connect_params,
                cursor_params=self.cursor_params,
                sql_parameters=self.sql_parameters,
                execute_params=self.execute_params)

    def trace_node(self, stats, root, connections):

        operation = self.operation

        # TODO Verify that these are the correct names to use.
        # Could possibly cache this if necessary.

        if operation in ('select', 'update', 'insert', 'delete'):
            target = self.target
            if target:
                name = 'Database/%s/%s' % (target, operation)
            else:
                name = 'Database/%s' % operation
        elif operation in ('show',):
            name = 'Database/%s' % operation
        else:
            name = 'Database/other/sql'

        name = root.string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        params = {}

        sql = self.formatted

        if sql:
            # Limit the length of any SQL that is reported back.

            limit = root.settings.agent_limits.sql_query_length_maximum

            params['sql'] = root.string_table.cache(sql[:limit])

            if self.stack_trace:
                params['backtrace'] = [root.string_table.cache(x) for x in
                        self.stack_trace]

            # Only perform an explain plan if this node ended up being
            # flagged to have an explain plan. This is applied when cap
            # on number of explain plans for whole harvest period is
            # applied across all transaction traces just prior to the
            # transaction traces being generated.

            if getattr(self, 'generate_explain_plan', None):
                explain_plan_data = explain_plan(connections,
                        self.statement, self.connect_params,
                        self.cursor_params, self.sql_parameters,
                        self.execute_params, self.sql_format)

                if explain_plan_data:
                    params['explain_plan'] = explain_plan_data

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)
