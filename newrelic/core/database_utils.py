"""Database utilities consists of routines for obfuscating SQL, retrieving
explain plans for SQL etc.

"""

import logging
import re
import time
import weakref

from newrelic.core.internal_metrics import (internal_trace, internal_metric)

# Various actions are dependent on the database being used. For most
# flexibility we use the name of the Python module used as client.
# falling back to allowing a string name also to be passed in. This does
# mean we are limited to what specific client modules we are supporting
# and not easy for a user to apply generic DBAPI2 instrumentation to
# another module. Need to investigate a better way of handling that at
# some point.

def _dbapi_name(dbapi):
    return dbapi and hasattr(dbapi, '__name__') and dbapi.__name__ or dbapi

# Obfuscation of SQL is done when reporting SQL statements back to the
# data collector so that sensitive information is not being passed.
# Obfuscation consists of replacing any quoted strings, integer or float
# literals with a '?'. For quoted strings which types of quoted strings
# should be collapsed depend on the database in use.

# See http://stackoverflow.com/questions/6718874.
#
# Escaping of quotes in SQL isn't like normal C style string. That is,
# no backslash. Uses two successive instances of quote character in
# middle of the string to indicate one embedded quote.

_single_quotes_p = "'(?:[^']|'')*'"
_double_quotes_p = '"(?:[^"]|"")*"'
_any_quotes_p = _single_quotes_p + '|' + _double_quotes_p

_single_quotes_re = re.compile(_single_quotes_p)
_double_quotes_re = re.compile(_double_quotes_p)
_any_quotes_re = re.compile(_any_quotes_p)

# See http://www.regular-expressions.info/examplesprogrammer.html.
#
# Is important to take word boundaries into consideration so we do not
# match numbers which are used on the end of identifiers. Technically
# this will not match numbers on the start of identifiers even though
# leading digits on identifiers aren't valid anyway. As it shouldn't
# occur, shouldn't be an issue.
#
# We add one variation here in that don't want to replace a number that
# follows on from a ':'. This is because ':1' can be used as positional
# parameter with database adapters where 'paramstyle' is 'numeric'.

_int_re = re.compile(r'(?<!:)\b\d+\b')

_quotes_table = {
    'MySQLdb': _any_quotes_re,
}

_quotes_default = _single_quotes_re

@internal_trace('Supportability/DatabaseUtils/Calls/obfuscate_sql')
def _obfuscate_sql(sql, dbapi=None):
    name = _dbapi_name(dbapi)

    quotes_re = _quotes_table.get(name, _quotes_default)

    # Substitute quoted strings first.

    sql = quotes_re.sub('?', sql)

    # Replace straight integer values. This will pick up
    # integers by themselves but also as part of floating point
    # numbers. Because of word boundary checks in pattern will
    # not match numbers within identifier names.

    sql = _int_re.sub('?', sql)

    return sql

# Normalization of the SQL is done so that when we can produce a hash
# value for a slow SQL such that it generates the same value for two SQL
# statements where only difference is values that may have been used.
#
# The main thing we need to contend with is the value sets where can
# have variable numbers of values for which we collapse them down to a
# single value. We also need to replace all the different variations of
# param styles with a '?'. This is in case in one situation a literal
# was used but in another it was a param, but param style is something
# other than '?' that literals are otherwise converted to. We also strip
# out all whitespace between identifiers and non identifiers to cope
# with varying amounts being used in different cases. A single space is
# left between identifiers.
#
# Note that we pickup up both ':1' and ':name' with the sub pattern
# ':\w+'. This can match ':1name', which is not strictly correct, but
# then it likely isn't valid in SQL anyway for that param style.

_normalize_params_1_p = r'%\([^)]*\)s'
_normalize_params_1_re = re.compile(_normalize_params_1_p)
_normalize_params_2_p = r'%s'
_normalize_params_2_re = re.compile(_normalize_params_2_p)
_normalize_params_3_p = r':\w+'
_normalize_params_3_re = re.compile(_normalize_params_3_p)

_normalize_values_p = r'\([^)]+\)'
_normalize_values_re = re.compile(_normalize_values_p)

_normalize_whitespace_1_p = r'\s+'
_normalize_whitespace_1_re = re.compile(_normalize_whitespace_1_p)
_normalize_whitespace_2_p = r'\s+(?!\w)'
_normalize_whitespace_2_re = re.compile(_normalize_whitespace_2_p)
_normalize_whitespace_3_p = r'(?<!\w)\s+'
_normalize_whitespace_3_re = re.compile(_normalize_whitespace_3_p)

@internal_trace('Supportability/DatabaseUtils/Calls/normalize_sql')
def _normalize_sql(sql, dbapi):
    # Note we that do this as a series of regular expressions as
    # using '|' in regular expressions is more expensive.

    # Convert param style of '%(name)s' to '?'. We need to do
    # this before collapsing sets of values to a single value
    # due to the use of the parenthesis in the param style.

    sql = _normalize_params_1_re.sub('?', sql)

    # Collapse any parenthesised set of values to a single value.

    sql = _normalize_values_re.sub('(?)', sql)

    # Convert '%s', ':1' and ':name' param styles to '?'.

    sql = _normalize_params_2_re.sub('?', sql)
    sql = _normalize_params_3_re.sub('?', sql)

    # Strip leading and trailing white space.

    sql = sql.strip()

    # Collapse multiple white space to single white space.

    sql = _normalize_whitespace_1_re.sub(' ', sql)

    # Drop spaces adjacent to identifier except for case where
    # identifiers follow each other.

    sql = _normalize_whitespace_2_re.sub('', sql)
    sql = _normalize_whitespace_3_re.sub('', sql)

    return sql

# Helper function for extracting out any identifier from a string which
# might be preceded or followed by punctuation which we can expect in
# context of SQL statements.
#
# XXX This is going to fail for various cases. For details on naming
# rules for database table names see:
#
# http://www.informit.com/articles/article.aspx?p=377068

#_identifier_re = re.compile('["`\[\]]*')
_identifier_re = re.compile('[\',"`\[\]\(\)]*')

def _extract_identifier(token):
    return _identifier_re.sub('', token).strip().lower()

# Helper function for removing C style comments embedded in SQL statements.

_uncomment_sql_p = r'/\*.*?\*/'
_uncomment_sql_re = re.compile(_uncomment_sql_p, re.DOTALL)

def _uncomment_sql(sql, dbapi):
    return _uncomment_sql_re.sub('', sql)

# Parser routines for the different SQL statement operation types.

def _parse_default(sql, regex):
    match = regex.search(sql)
    return match and _extract_identifier(match.group(1)) or ''

_parse_from_p = r'\s+FROM\s+(?!\()(\S+)'
_parse_from_re = re.compile(_parse_from_p, re.IGNORECASE)

_parse_into_p = r'\s+INTO\s+(?!\()(\S+)'
_parse_into_re = re.compile(_parse_into_p, re.IGNORECASE)

_parse_update_p = r'\s*UPDATE\s+(?!\()(\S+)'
_parse_update_re = re.compile(_parse_update_p, re.IGNORECASE)

_parse_table_p = r'\s+TABLE\s+(?!\()(\S+)'
_parse_table_re = re.compile(_parse_table_p, re.IGNORECASE)

_parse_call_p = r'\s*CALL\s+(?!\()(\w+)'
_parse_call_re = re.compile(_parse_call_p, re.IGNORECASE)

_parse_show_p = r'\s*SHOW\s+(.*)'
_parse_show_re = re.compile(_parse_show_p, re.IGNORECASE | re.DOTALL)

_parse_set_p = r'\s*SET\s+(.*?)\W+.*'
_parse_set_re = re.compile(_parse_set_p, re.IGNORECASE | re.DOTALL)

_parse_exec_p = r'\s*EXEC\s+(?!\()(\w+)'
_parse_exec_re = re.compile(_parse_exec_p, re.IGNORECASE)

_parse_execute_p = r'\s*EXECUTE\s+(?!\()(\w+)'
_parse_execute_re = re.compile(_parse_execute_p, re.IGNORECASE)

_parse_alter_p = r'\s*ALTER\s+(?!\()(\w+)'
_parse_alter_re = re.compile(_parse_alter_p, re.IGNORECASE)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_select')
def _parse_select(sql, dbapi):
    return _parse_default(sql, _parse_from_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_delete')
def _parse_delete(sql, dbapi):
    return _parse_default(sql, _parse_from_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_insert')
def _parse_insert(sql, dbapi):
    return _parse_default(sql, _parse_into_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_update')
def _parse_update(sql, dbapi):
    return _parse_default(sql, _parse_update_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_create')
def _parse_create(sql, dbapi):
    return _parse_default(sql, _parse_table_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_drop')
def _parse_drop(sql, dbapi):
    return _parse_default(sql, _parse_table_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_call')
def _parse_call(sql, dbapi):
    return _parse_default(sql, _parse_call_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_show')
def _parse_show(sql, dbapi):
    return _parse_default(sql, _parse_show_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_set')
def _parse_set(sql, dbapi):
    return _parse_default(sql, _parse_set_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_exec')
def _parse_exec(sql, dbapi):
    return _parse_default(sql, _parse_exec_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_execute')
def _parse_execute(sql, dbapi):
    return _parse_default(sql, _parse_execute_re)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target_alter')
def _parse_alter(sql, dbapi):
    return _parse_default(sql, _parse_alter_re)

_operation_table = {
    'select': _parse_select,
    'delete': _parse_delete,
    'insert': _parse_insert,
    'update': _parse_update,
    'create': _parse_create,
    'drop': _parse_drop,
    'call': _parse_call,
    'show': _parse_show,
    'set': _parse_set,
    'exec': _parse_exec,
    'execute': _parse_execute,
    'alter': _parse_alter,
}

_parse_operation_p = r'(\w+)'
_parse_operation_re = re.compile(_parse_operation_p)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_operation')
def _parse_operation(sql, dbapi):
    match = _parse_operation_re.search(sql)
    operation = match and match.group(1).lower() or ''
    return operation if operation in _operation_table else ''

@internal_trace('Supportability/DatabaseUtils/Calls/parse_target')
def _parse_target(sql, dbapi, operation):
    parse = _operation_table.get(operation, None)
    return parse and parse(sql, dbapi) or ''

_explain_plan_table = {
    'MySQLdb': 'EXPLAIN',
    'postgresql.interface.proboscis.dbapi2': 'EXPLAIN',
    'psycopg2': 'EXPLAIN',
    'sqlite3.dbapi2': 'EXPLAIN QUERY PLAN',
}

@internal_trace('Supportability/DatabaseUtils/Calls/explain_plan')
def _explain_plan(sql, dbapi, connect_params, cursor_params, execute_params):
    if dbapi is None:
        return None
    if type(dbapi) == type(''):
        return None

    name = _dbapi_name(dbapi)

    if name is None:
        return None

    if connect_params is None:
        return None
    if cursor_params is None:
        return None
    if execute_params is None:
        return None

    query = None

    command = _explain_plan_table.get(name)

    if not command:
        return None

    query = '%s %s' % (command, sql)

    args, kwargs = connect_params
    try:
        connection = dbapi.connect(*args, **kwargs)
        try:
            args, kwargs = cursor_params
            cursor = connection.cursor(*args, **kwargs)
            try:
                args, kwargs = execute_params
                cursor.execute(query, *args, **kwargs)
                columns = []
                if cursor.description:
                    for column in cursor.description:
                        columns.append(column[0])
                rows = cursor.fetchall()
                if not columns and not rows:
                    return None
                return (columns, rows)
            except:
                pass
            finally:
                cursor.close()
        finally:
            connection.close()
    except:
        pass

    return None

class SQLStatement(object):

    def __init__(self, sql, dbapi=None):
        self.sql = sql
        self.dbapi = dbapi

        self._operation = None
        self._target = None
        self._uncommented = None
        self._obfuscated = None
        self._normalized = None
        self._identifier = None

    @property
    def operation(self):
        if self._operation is None:
            self._operation = _parse_operation(self.uncommented, self.dbapi)
        return self._operation

    @property
    def target(self):
        if self._target is None:
            self._target = _parse_target(self.uncommented, self.dbapi,
                    self.operation)
        return self._target

    @property
    def uncommented(self):
        if self._uncommented is None:
            self._uncommented = _uncomment_sql(self.sql, self.dbapi)
        return self._uncommented

    @property
    def obfuscated(self):
        if self._obfuscated is None:
            self._obfuscated = _obfuscate_sql(self.uncommented, self.dbapi)
        return self._obfuscated

    @property
    def normalized(self):
        if self._normalized is None:
            self._normalized = _normalize_sql(self.obfuscated, self.dbapi)
        return self._normalized

    @property
    def identifier(self):
        if self._identifier is None:
            self._identifier = hash(self.normalized)
        return self._identifier

    def formatted(self, format):
        if format == 'off':
            return ''

        elif format == 'raw':
            return self.sql

        else:
            return self.obfuscated

    def explain_plan(self, connect_params, cursor_params, execute_params):
        return _explain_plan(self.sql, self.dbapi, connect_params,
                cursor_params, execute_params)

_sql_statements = weakref.WeakValueDictionary()

def sql_statement(sql, dbapi):
    key = (sql, dbapi)

    result = _sql_statements.get(key, None)

    if result is not None:
        return result

    result = SQLStatement(sql, dbapi)
    _sql_statements[key] = result

    return result
