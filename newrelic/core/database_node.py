try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.metric
import newrelic.core.trace_node

from newrelic.core.database_utils import (obfuscated_sql, parsed_sql,
                                          explain_plan)

def formatted_sql(dbapi, format, sql):
    if format == 'off':
        return ''

    # FIXME Need to implement truncation somewhere.

    if format == 'raw':
        return sql

    name = dbapi and dbapi.__name__ or None 

    return obfuscated_sql(name, sql)

_SlowSqlNode = namedtuple('_SlowSqlNode',
        ['duration', 'path', 'request_uri', 'sql', 'sql_format',
        'metric', 'dbapi', 'stack_trace', 'connect_params',
        'cursor_params', 'execute_params'])

class SlowSqlNode(_SlowSqlNode):

    @property
    def sql_id(self):
        name = self.dbapi and self.dbapi.__name__ or None 
        return obfuscated_sql(name, self.sql, collapsed=True)

    @property
    def formatted_sql(self):
        return formatted_sql(self.dbapi, self.sql_format, self.sql)

    @property
    def explain_plan(self):
        return explain_plan(self.dbapi, self.sql, self.connect_params,
                            self.cursor_params, self.execute_params)

_DatabaseNode = namedtuple('_DatabaseNode',
        ['dbapi',  'sql', 'children', 'start_time', 'end_time', 'duration',
        'exclusive', 'stack_trace', 'sql_format', 'connect_params',
        'cursor_params', 'execute_params'])

class DatabaseNode(_DatabaseNode):

    @property
    def parsed_sql(self):
        name = self.dbapi and self.dbapi.__name__ or None 
        return parsed_sql(name, self.sql)

    @property
    def explain_plan(self):
        return explain_plan(self.dbapi, self.sql, self.connect_params,
                            self.cursor_params, self.execute_params)

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.

        """

        yield newrelic.core.metric.TimeMetric(name='Database/all',
            scope='', overflow=None, forced=True, duration=self.duration,
            exclusive=self.exclusive)

        if root.type == 'WebTransaction':
            yield newrelic.core.metric.TimeMetric(name='Database/allWeb',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)
        else:
            yield newrelic.core.metric.TimeMetric(name='Database/allOther',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

        # FIXME The follow is what PHP agent was doing, but it may
        # not sync up with what is now actually required. As example,
        # the 'show' operation in PHP agent doesn't generate a full
        # path with a table name, yet get_table() in SQL parser
        # does appear to generate one. Also, the SQL parser has
        # special cases for 'set', 'create' and 'call' as well.

        table, operation = self.parsed_sql

        if operation in ('select', 'update', 'insert', 'delete'):
            name = 'Database/%s/%s' % (table, operation)
            overflow = 'Database/*/%s' % operation
            scope = root.path

            yield newrelic.core.metric.TimeMetric(name=name, scope='',
                    overflow=overflow, forced=False, duration=self.duration,
                    exclusive=self.exclusive)

            yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                    overflow=overflow, forced=False, duration=self.duration,
                    exclusive=self.exclusive)

            name = 'Database/%s' % operation

            yield newrelic.core.metric.TimeMetric(name=name,
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

        elif operation in ('show',):
            name = 'Database/%s' % operation
            scope = root.path

            yield newrelic.core.metric.TimeMetric(name=name,
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

            yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                    overflow=None, forced=True, duration=self.duration,
                    exclusive=self.exclusive)

        else:
            yield newrelic.core.metric.TimeMetric(name='Database/other',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

            yield newrelic.core.metric.TimeMetric(name='Database/other/sql',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

            scope = root.path

            yield newrelic.core.metric.TimeMetric(name='Database/other/sql',
                scope=scope, overflow=None, forced=True, duration=self.duration,
                exclusive=self.exclusive)

        # XXX Ignore the children as this should be a terminal node.

        #for child in self.children:
        #    for metric in child.time_metrics(stats, root, self):
        #        yield metric

    def slow_sql_node(self, stats, root):

        table, operation = self.parsed_sql

        if operation in ('select', 'update', 'insert', 'delete'):
            name = 'Database/%s/%s' % (table, operation)
        elif operation in ('show',):
            name = 'Database/%s' % operation
        else:
            name = 'Database/other/sql'

        request_uri = ''
        if root.type == 'WebTransaction':
            request_uri = root.request_uri

        # Limit the length of any SQL that is reported back.

        limit = root.settings.agent_limits.sql_query_length_maximum

        sql = self.sql[:limit]

        return SlowSqlNode(duration=self.duration, path=root.path,
                request_uri=request_uri, sql=sql,
                sql_format=self.sql_format, metric=name,
                dbapi=self.dbapi, stack_trace=self.stack_trace,
                connect_params=self.connect_params,
                cursor_params=self.cursor_params,
                execute_params=self.execute_params)

    def trace_node(self, stats, string_table, root):

        table, operation = self.parsed_sql

        # TODO Verify that these are the correct names to use.
        # Could possibly cache this if necessary.

        if operation in ('select', 'update', 'insert', 'delete'):
            name = 'Database/%s/%s' % (table, operation)
        elif operation in ('show',):
            name = 'Database/%s' % operation
        else:
            name = 'Database/other/sql'

        name = string_table.cache(name)

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)

        # XXX Ignore the children as this should be a terminal node.

        #children = [child.trace_node(stats, string_table, root) for
        #            child in self.children]
        children = []

        root.trace_node_count += 1

        params = {}

        sql = formatted_sql(self.dbapi, self.sql_format, self.sql)

        if sql:
            # Limit the length of any SQL that is reported back.

            limit = root.settings.agent_limits.sql_query_length_maximum

            params['sql'] = string_table.cache(sql[:limit])

            if self.stack_trace:
                params['backtrace'] = map(string_table.cache, self.stack_trace)

            explain_plan = self.explain_plan
            if explain_plan:
                params['explain_plan'] = explain_plan

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=None)
