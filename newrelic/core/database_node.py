import itertools
import urlparse
import re

try:
    from collections import namedtuple
except:
    from newrelic.lib.namedtuple import namedtuple

import newrelic.core.metric
import newrelic.core.trace_node
import newrelic.core.database_utils

_DatabaseNode = namedtuple('_DatabaseNode',
        ['dbapi', 'connect_params', 'sql', 'children',
        'start_time', 'end_time', 'duration', 'exclusive',
        'stack_trace', 'sql_format'])

class DatabaseNode(_DatabaseNode):

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

        table, operation = stats.parsed_sql(self.sql)

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

        # Now for the children.

	# TODO Above exclusive times don't take into
	# consideration children if any existed. Still need to
	# work out how such children to this nodes is meant to
	# work.

        for child in self.children:
            for metric in child.time_metrics(stats, root, self):
                yield metric

    def sql_trace_node(self, stats, root):

        table, operation = stats.parsed_sql(self.sql)

        # TODO Verify that these are the correct names to use.
        # Could possibly cache this if necessary.

        if operation in ('select', 'update', 'insert', 'delete'):
            name = 'Database/%s/%s' % (table, operation)
        elif operation in ('show',):
            name = 'Database/%s' % operation
        else:
            name = 'Database/other/sql'

        duration = self.duration

        sql = stats.formatted_sql(self.dbapi, self.sql_format, self.sql)

        # FIXME This is where we need to generate the data structure,
        # likely a dictionary for holding single sql trace. Believe
        # that node needs to hold the metric name, duration and sql
        # but not sure how each is identified. Could even be a tuple.

        # yield ?????

    def trace_node(self, stats, root):

        table, operation = stats.parsed_sql(self.sql)

        # TODO Verify that these are the correct names to use.
        # Could possibly cache this if necessary.

        if operation in ('select', 'update', 'insert', 'delete'):
            name = 'Database/%s/%s' % (table, operation)
        elif operation in ('show',):
            name = 'Database/%s' % operation
        else:
            name = 'Database/other/sql'

        start_time = newrelic.core.trace_node.node_start_time(root, self)
        end_time = newrelic.core.trace_node.node_end_time(root, self)
        children = [child.trace_node(stats, root) for child in self.children]

        sql = stats.formatted_sql(self.dbapi, self.sql_format, self.sql)

        params = { 'sql': sql }

        if self.stack_trace:
            params['backtrace'] = self.stack_trace

        return newrelic.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children)
