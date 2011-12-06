try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.metric
import newrelic.core.trace_node

from newrelic.core.database_utils import obfuscated_sql, parsed_sql

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
        'metric', 'dbapi', 'connect_params', 'stack_trace'])

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
        return None

_DatabaseNode = namedtuple('_DatabaseNode',
        ['dbapi', 'connect_params', 'sql', 'children',
        'start_time', 'end_time', 'duration', 'exclusive',
        'stack_trace', 'sql_format'])

class DatabaseNode(_DatabaseNode):

    @property
    def parsed_sql(self):
        name = self.dbapi and self.dbapi.__name__ or None 
        return parsed_sql(name, self.sql)

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

        return SlowSqlNode(duration=self.duration, path=root.path,
                request_uri=request_uri, sql=self.sql,
                sql_format=self.sql_format, metric=name,
                dbapi=self.dbapi, connect_params=self.connect_params,
                stack_trace=self.stack_trace)

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

        params = {}

        sql = formatted_sql(self.dbapi, self.sql_format, self.sql)

        if sql:
            params['sql'] = string_table.cache(sql)

            if self.stack_trace:
                params['backtrace'] = map(string_table.cache, self.stack_trace)

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children)
