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
    def metric_name(self, type=None):
        parsed_sql = SqlParser(self.sql)
        return "Database/%s/%s" % (parsed_sql.table, parsed_sql.operation)

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

        # TODO Need to fill out the remainder of the database
        # metrics but to do that need a mini parser to extract
        # the type of SQL operation and the table name. Need to
        # remember to do the scope metrics as well.

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
        
