import collections
import itertools
import urlparse
import re

import newrelic.core.metric
import newrelic.lib.sqlparse
import newrelic.lib.sqlparse.sql
import newrelic.lib.sqlparse.tokens

_DatabaseNode = collections.namedtuple('_DatabaseNode',
        ['database_module', 'connect_params', 'sql', 'children',
        'start_time', 'end_time', 'duration', 'exclusive',
        'stack_trace'])

class DatabaseNode(_DatabaseNode):

    def metric_name(self):
        # FIXME This isn't actually useful as a standalone
        # method as we need to generate different numbers of
        # metrics based on whether table could be derived or
        # when not what the operation is. See below.

        parsed_sql = SqlParser(self.sql)
        return "Database/%s/%s" % (parsed_sql.table, parsed_sql.operation)

    def parsed_sql(self):
        # FIXME The SqlParser class doesn't cope well with badly
        # formed input data, so need to catch exceptions here.

        try:
            parsed_sql = SqlParser(self.sql)
            table = parsed_sql.table
            operation = parsed_sql.operation
        except:
            table = None
            operation = None

        return table, operation

    def time_metrics(self, root, parent):
        """Return a generator yielding the timed metrics for this
        database node as well as all the child nodes.

        """

        yield newrelic.core.metric.TimeMetric(name='Database/all',
            scope='', overflow=None, forced=True, duration=self.duration,
            exclusive=None)

        if root.type == 'WebTransaction':
            yield newrelic.core.metric.TimeMetric(name='Database/allWeb',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)
        else:
            yield newrelic.core.metric.TimeMetric(name='Database/allOther',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

        # FIXME The follow is what PHP agent was doing, but it may
        # not sync up with what is now actually required. As example,
        # the 'show' operation in PHP agent doesn't generate a full
        # path with a table name, yet get_table() in SQL parser
        # does appear to generate one. Also, the SQL parser has
        # special cases for 'set', 'create' and 'call' as well.

        table, operation = self.parsed_sql()

        if operation in ('select', 'update', 'insert', 'delete'):
            name = 'Database/%s/%s' % (table, operation)
            overflow = 'Database/*/%s' % operation
            scope = root.path

            yield newrelic.core.metric.TimeMetric(name=name, scope='',
                    overflow=overflow, forced=False, duration=self.duration,
                    exclusive=None)

            yield newrelic.core.metric.TimeMetric(name=name, scope=scope,
                    overflow=overflow, forced=False, duration=self.duration,
                    exclusive=None)

            name = 'Database/%s' % operation

            yield newrelic.core.metric.TimeMetric(name=name,
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

        elif operation in ('show',):
            name = 'Database/%s' % operation

            yield newrelic.core.metric.TimeMetric(name=name,
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

        else:
            yield newrelic.core.metric.TimeMetric(name='Database/other',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

            yield newrelic.core.metric.TimeMetric(name='Database/other/sql',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

            scope = root.path

            yield newrelic.core.metric.TimeMetric(name='Database/other/sql',
                scope='', overflow=None, forced=True, duration=self.duration,
                exclusive=None)

        # Now for the children.

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric

class SqlParser:
    def __init__(self, sql):
        self.stmt = newrelic.lib.sqlparse.parse(sql)[0]
        self.operation = self.get_operation()
        self.table = self.get_table()

    def get_operation(self):
        ddl = self.stmt.token_next_by_type(0, 
                     newrelic.lib.sqlparse.tokens.Keyword.DDL)
        dml = self.stmt.token_next_by_type(0, 
                     newrelic.lib.sqlparse.tokens.Keyword.DML)
        if ddl and not dml:
            return ddl.value.lower()
        elif dml and not ddl:
            return dml.value.lower()
        elif ddl and dml:
            if self.stmt.token_index(ddl) < self.stmt.token_index(dml):
                return ddl.value.lower()
            else:
                return dml.value.lower()
        else:
            keyword = self.stmt.token_next_by_type(0, 
                     newrelic.lib.sqlparse.tokens.Keyword)
            return keyword.value.lower()

    def get_table(self):
        if self.operation == 'select' or self.operation == 'delete':
            token = self._find_table_token_for(newrelic.lib.sqlparse.tokens.Keyword, 'FROM')
        elif self.operation == 'update':
            token = self._find_table_token_for(newrelic.lib.sqlparse.tokens.Keyword.DML, 'UPDATE')
        elif self.operation == 'set' or self.operation == 'show':
            token = self._find_table_token_for(newrelic.lib.sqlparse.tokens.Keyword, self.operation.upper())
        elif self.operation == 'insert':
            token = self._find_table_token_for(newrelic.lib.sqlparse.tokens.Keyword, 'INTO')
        elif self.operation == 'create':
            idx = self._find_idx_for(newrelic.lib.sqlparse.tokens.Keyword.DDL, 'CREATE') 
            token = self.stmt.token_next_by_type(idx + 1, newrelic.lib.sqlparse.tokens.Keyword)
        elif self.operation == 'call':
            self.operation = 'ExecuteProcedure'
            token = self._find_table_token_for(newrelic.lib.sqlparse.tokens.Keyword, 'CALL')
        else:
            token = None

        if token is not None:
            return self._format_table_token(token)

    def _get_first_identifier_after(self, idx):
        for token in self.stmt.tokens[idx:]:
            if token.__class__.__name__ == 'Identifier':
                return token
            elif token.__class__.__name__ == 'IdentifierList':
                first_table_token = token.get_identifiers()[0]
                return first_table_token
            elif token.__class__.__name__ == 'Function':
                return token

    def _format_table_token(self, token):
        table_name = re.sub('[",`,\[,\]]*', '', token.to_unicode()).lower()
        if token.__class__.__name__ == 'Function':
            return re.sub('\(.*', '', table_name)
        return table_name

    def _find_idx_for(self, ttype, match):
        node = self.stmt.token_next_match(0, ttype, match)
        return self.stmt.token_index(node)
        

    def _find_table_token_for(self, ttype, match):
        idx = self._find_idx_for(ttype, match)
        return self._get_first_identifier_after(idx)
        
