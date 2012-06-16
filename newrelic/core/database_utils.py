"""Database utilities consists of routines for obfuscating SQL, retrieving
explain plans for SQL etc.

"""

import logging
import re
import time
import weakref

import newrelic.lib.sqlparse
import newrelic.lib.sqlparse.sql
import newrelic.lib.sqlparse.tokens

from newrelic.core.config import global_settings
from newrelic.core.internal_metrics import (internal_trace, internal_metric)

_logger = logging.getLogger(__name__)

_settings = global_settings()

# Caching mechanism for storing generated results from operations on
# database queries. Values are kept in a weak value dictionary with
# moving history of buckets also holding the value so not removed from
# the dictionary. The cached should be expired on each harvest loop
# iteration. To allow for preservation of frequently used results, a
# number of the buckets retaining history should be kept when cache is
# expired.
#
# Note that there is no thread locking on this and that should not be an
# issue. It will mean that there is a race condition for adding entries,
# but since result will always be the same, doesn't matter if work
# duplicated in this rare case.

class SqlProperties(object):

    def __init__(self, sql):
        self.sql = sql
        self.obfuscated = None
        self.obfuscated_collapsed = None
        self.parsed = None

class SqlPropertiesCache(object):

    def __init__(self):
        self.__cache = weakref.WeakValueDictionary()
        self.__history = [set()]

    def fetch(self, sql):
        entry = self.__cache.get(sql, None)

        if entry is None:
            entry = SqlProperties(sql)
            self.__cache[sql] = entry

            if _settings.debug.log_sql_cache_misses:
                _logger.info('SQL cache miss occurred for SQL of %r.', sql)

            internal_metric('Supportability/DatabaseUtils/Cache/Misses', 1)
        else:
            internal_metric('Supportability/DatabaseUtils/Cache/Hits', 1)

        self.__history[0].add(entry)
        return entry

    def expire(self, keep):
        self.__history.insert(0, set())
        self.__history = self.__history[:keep+1]

sql_properties_cache = SqlPropertiesCache()

# See http://stackoverflow.com/questions/6718874.
#
# Escaping of quotes in SQL isn't like normal C style string.
# That is, no backslash. Uses two successive instances of quote
# character in middle of the string to indicate one embedded
# quote.

_single_quotes_pattern = "'(?:[^']|'')*'"
_double_quotes_pattern = '"(?:[^"]|"")*"'
_any_quotes_pattern = _single_quotes_pattern + '|' + _double_quotes_pattern

_single_quotes_re = re.compile(_single_quotes_pattern)
_double_quotes_re = re.compile(_double_quotes_pattern)
_any_quotes_re = re.compile(_any_quotes_pattern)

# See http://www.regular-expressions.info/examplesprogrammer.html.
#
# Is important to take word boundaries into consideration so we
# do not match numbers which are used on the end of identifiers.
# Technically this will not match numbers on the start of
# identifiers even though leading digits on identifiers aren't
# valid anyway. As it shouldn't occur, shouldn't be an issue.
#
# We add one variation here in that don't want to replace a
# number that follows on from a ':'. This is because ':1' can be
# used as positional parameter with database adapters where
# 'paramstyle' is 'numeric'.
#
# TODO Probably should look at 'paramstyle' attribute of the
# database adapter module and be specific about what pattern we
# use. Don't at this point believe though that a numeric can
# follow a ':' in SQL statements otherwise so should be safe
# to do this.

_int_re = re.compile(r'(?<!:)\b\d+\b')

# Obfuscation can produce sets as '(?,?)'. Need to be able to
# collapse these to single value set. Also need to deal with
# parameterised values which can be '?', ':1', ':name', '%s' or
# '%(name)s'.
#
# Note that we pickup up both ':1' and ':name' with the sub
# pattern ':\w+'. This can match ':1name', which is not strictly
# correct, but then it likely isn't valid in SQL anyway for
# that param style.
#
# TODO We could also look at 'paramstyle' attribute here as
# well and be more specific, but this comes after strings are
# replaced and so shouldn't really find these patterns unless
# actually in use as wouldn't be valid SQL otherwise.

_one_value_p = r'\s*(\?|%s|:\w+|%s|%\([^)]*\)s)\s*'
_list_values_p = r'\(' + _one_value_p + r'(\s*,' + _one_value_p + r')*\s*\)'

_collapse_set_re = re.compile(_list_values_p)

@internal_trace('Supportability/DatabaseUtils/Calls/obfuscated_sql')
def obfuscated_sql(name, sql, collapsed=False):
    """Returns obfuscated version of the sql. The quoting
    convention is determined by looking at the name of the
    database module supplied. Obfuscation consists of replacing
    literal strings and integers. Collapsing of values in sets
    is optional.

    """

    entry = sql_properties_cache.fetch(sql)

    if entry.obfuscated is not None:
        if collapsed:
            return entry.obfuscated_collapsed
        return entry.obfuscated

    # Substitute quoted strings first. In the case of MySQL it
    # uses back quotes around table names so safe to replace
    # contents of strings using either single of double quotes.
    # For PostgreSQL and other databases, double quotes are used
    # around table names so only replace contents of single
    # quoted strings.

    if name in ['MySQLdb']:
        obfuscated = _any_quotes_re.sub('?', sql)
    else:
        obfuscated = _single_quotes_re.sub('?', sql)

    # Finally replace straight integer values. This will pick
    # up integers by themselves but also as part of floating
    # point numbers. Because of word boundary checks in pattern
    # will not match numbers within identifier names.

    obfuscated = _int_re.sub('?', obfuscated)

    # Collapse sets of values used in IN clauses to a single.
    # This form of obfuscated SQL will be used when generating
    # ID for slow SQL samples as well as be SQL which the table
    # and operation are derived from. This is used for the latter
    # as large sets will slow down the SQL parser dramatically.

    obfuscated_collapsed = _collapse_set_re.sub('(?)', obfuscated)

    entry.obfuscated = obfuscated
    entry.obfuscated_collapsed = obfuscated_collapsed

    if collapsed:
        return obfuscated_collapsed

    return obfuscated

# Helper function for extracting out any identifier from a string which
# might be preceded or followed by punctuation which we can expect in
# context of SQL statements.
#
# Note that it may be better to match and extract on the characters of
# the first identifier in string rather than trying to remove everything
# else.

#_identifier_re = re.compile('["`\[\]]*')
_identifier_re = re.compile('[\',"`\[\]\(\)]*')

def _extract_identifier(token):
    return _identifier_re.sub('', token).strip().lower()

# SQL parser routines for where using sqlparse the library.

@internal_trace('Supportability/DatabaseUtils/Calls/parse_select')
def _parse_select(statement, token):
    # For 'select' we need to look for 'from'. The argument to
    # 'from' can be a single table name, a list of table names
    # or a sub query.

    from_token = statement.token_next_match(token,
            newrelic.lib.sqlparse.tokens.Keyword, 'from')

    if from_token is None:
        return None

    argument = statement.token_next(from_token)

    if argument is None:
        return None

    # Where it is a list of table names we grab the first in the
    # list and use it alone. Seems that sub queries also get
    # bundled up this way sometimes as well, but doesn't matter
    # as following handles it anyway.

    if type(argument) == newrelic.lib.sqlparse.sql.IdentifierList:
        argument = argument.get_identifiers()[0]

    # Now we need to check whether it is actually a sub query.
    # In this case we pull the data from the token list for the
    # sub query instead. We need though to deal with a couple of
    # different cases for the sub query which sqlparse library
    # handles differently.

    if isinstance(argument, newrelic.lib.sqlparse.sql.TokenList):

        first_token = argument.token_first()

        if type(first_token) == newrelic.lib.sqlparse.sql.Parenthesis:

            # For a token list, if the first token is a parenthesis
            # group, then it is a sub query. We extract the sub
            # query from the parenthesis group, drop leading and
            # trailing parenthesis.

            tokens = first_token.tokens[1:-1]
            token_list = newrelic.lib.sqlparse.sql.TokenList(tokens)
            (identifier, operation) = _parse_token_list(token_list)
            return identifier

        elif (type(first_token) == newrelic.lib.sqlparse.sql.Token and
                first_token.ttype == newrelic.lib.sqlparse.tokens.Punctuation
                and first_token.value == '('):

            # For some cases of a sub query, then it seems to not
            # get parsed out correctly and so we end up with a
            # normal token stream with punctuation value '('
            # indicating start of a sub query. We leave the closing
            # parenthesis and any alias on the list of tokens but
            # that doesn't seem to cause any problems.

            index_first = argument.token_index(first_token)
            tokens = argument.tokens[index_first+1:]
            token_list = newrelic.lib.sqlparse.sql.TokenList(tokens)
            (identifier, operation) = _parse_token_list(token_list)
            return identifier

        # As table names can be aliased, we still only use the
        # first token so pick up the table name and not the full
        # string with alias.

        return _extract_identifier(first_token.to_unicode())

    elif (type(argument) == newrelic.lib.sqlparse.sql.Token and
            argument.ttype == newrelic.lib.sqlparse.tokens.Punctuation and
            argument.value == '('):

        # For some cases of a sub query, then it seems to not
        # get parsed out correctly and so we end up with a
        # normal token stream with punctuation value '('
        # indicating start of a sub query. We leave the closing
        # parenthesis and any alias on the list of tokens but
        # that doesn't seem to cause any problems.

        index_first = statement.token_index(argument)
        tokens = statement.tokens[index_first+1:]
        token_list = newrelic.lib.sqlparse.sql.TokenList(tokens)
        (identifier, operation) = _parse_token_list(token_list)
        return identifier

    return _extract_identifier(argument.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_delete')
def _parse_delete(statement, token):
    # For 'delete' we need to look for 'from'. The argument to
    # 'from' can be a single table name.

    from_token = statement.token_next_match(token,
            newrelic.lib.sqlparse.tokens.Keyword, 'from')

    if from_token is None:
        return None

    argument = statement.token_next(from_token)

    if argument is None:
        return None

    if isinstance(argument, newrelic.lib.sqlparse.sql.TokenList):
        first_token = argument.token_first()

        return _extract_identifier(first_token.to_unicode())

    return _extract_identifier(argument.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_insert')
def _parse_insert(statement, token):
    # For 'insert' we need to look for 'into'. The argument to
    # 'into' can be a single table name.

    into_token = statement.token_next_match(token,
            newrelic.lib.sqlparse.tokens.Keyword, 'into')

    if into_token is None:
        return None

    argument = statement.token_next(into_token)

    if argument is None:
        return None

    if isinstance(argument, newrelic.lib.sqlparse.sql.TokenList):
        first_token = argument.token_first()

        return _extract_identifier(first_token.to_unicode())

    return _extract_identifier(argument.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_update')
def _parse_update(statement, token):
    # For 'update' we need the immediately following argument.

    argument = statement.token_next(token)

    if argument is None:
        return None

    if isinstance(argument, newrelic.lib.sqlparse.sql.TokenList):
        first_token = argument.token_first()

        return _extract_identifier(first_token.to_unicode())

    return _extract_identifier(argument.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_create')
def _parse_create(statement, token):
    # For 'create' we need to look for 'table'. The argument to
    # 'table' should be a single table name.

    table_token = statement.token_next_match(token,
            newrelic.lib.sqlparse.tokens.Keyword, 'table')

    if table_token is None:
        return None

    argument = statement.token_next(table_token)

    if argument is None:
        return None

    if isinstance(argument, newrelic.lib.sqlparse.sql.TokenList):
        first_token = argument.token_first()

        return _extract_identifier(first_token.to_unicode())

    return _extract_identifier(argument.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_call')
def _parse_call(statement, token):
    # For 'call' we need the immediately following argument.

    argument = statement.token_next(token)

    if argument is None:
        return None

    if isinstance(argument, newrelic.lib.sqlparse.sql.TokenList):
        first_token = argument.token_first()

        return _extract_identifier(first_token.to_unicode())

    return _extract_identifier(argument.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_show')
def _parse_show(statement, token):
    # For 'show' we need all the following arguments.

    argument = statement.token_next(token)

    if argument is None:
        return None

    idx = statement.token_index(argument)
    tokens = statement.tokens[idx:]
    token_list = newrelic.lib.sqlparse.sql.TokenList(tokens)

    return _extract_identifier(token_list.to_unicode())

@internal_trace('Supportability/DatabaseUtils/Calls/parse_set')
def _parse_set(statement, token):
    # For 'set' we need all the following arguments bar the last
    # one which is the value the variable is being set to.

    argument = statement.token_next(token)

    if argument is None:
        return None

    idx = statement.token_index(argument)
    tokens = statement.tokens[idx:-1]
    token_list = newrelic.lib.sqlparse.sql.TokenList(tokens)

    return _extract_identifier(token_list.to_unicode())

_parser_table = {
    u'select': _parse_select,
    u'delete': _parse_delete,
    u'insert': _parse_insert,
    u'update': _parse_update,
    u'create': _parse_create,
    u'call': _parse_call,
    u'show': _parse_show,
    u'set': _parse_set,
}

def _parse_token_list(statement):
    # The operation will be the first non white space token in
    # the token. If no tokens at all then bail out.

    for token in statement.tokens:
        if not token.is_whitespace():
            break
    else:
        return (None, None)

    # Check for parenthesis group around the statement or part
    # thereof. We extract the inner statement from inside the
    # parenthesis group, dropping the leading and trailing
    # parenthesis and process again.
    #
    # TODO Note sure if need to also check for token with value
    # of '(' in this sort of situation.

    if type(token) == newrelic.lib.sqlparse.sql.Parenthesis:
        tokens = token.tokens[1:-1]
        token_list = newrelic.lib.sqlparse.sql.TokenList(tokens)
        return _parse_token_list(token_list)

    # Execute the parser for any operations we are interested
    # in. Any we don't care about will see table be returned
    # as None meaning it will be bundled under other SQL in
    # metrics.

    identifier = None
    operation = token.to_unicode().lower()

    parser = _parser_table.get(operation)
    if parser:
        identifier = parser(statement, token)

    if not identifier:
        operation = None

    return (identifier, operation)

def _parse_sql_statement_v1(sql):
    # The SQL could actually consist of multiple statements each
    # separated by a semicolon. The parse() routine splits out
    # each statement and returns a tuple holding each. We can
    # only report on one of the statements so use the first one.
    #
    # The parse() routine will raise an exception if not well
    # formed SQL that it can parse so need to catch that, ignore
    # it and then bail out.
    #
    # We optionally log details of the SQL if debug option enabled
    # to capture SQL statements which take longer than a certain
    # threshold to be parsed by the sqlparse library.

    internal_metric('Supportability/DatabaseUtils/Parse/Bytes', len(sql))

    try:
        if _settings.debug.sql_parsing_log_threshold is not None:
            start = time.time()

        statement = newrelic.lib.sqlparse.parse(sql)[0]

        if _settings.debug.sql_parsing_log_threshold is not None:
            duration = time.time() - start
            if duration >= _settings.debug.sql_parsing_log_threshold:
                _logger.info('Time spent parsing SQL exceeded the defined '
                        'threshold with duration of %.3f seconds. Please '
                        'report the details to New Relic support for '
                        'investigation. The SQL statement was %r.',
                        duration, sql)
    except:
        return (None, None)

    return _parse_token_list(statement)

# SQL parser routines for where using regex library.

_pattern_switches = re.IGNORECASE | re.DOTALL

_comment_pattern_re = re.compile(r'/\*.*?\*/', _pattern_switches)
_word_pattern_re = re.compile(r'\W*(\w+).*', _pattern_switches)

def _remove_comments(sql):
    return _comment_pattern_re.sub('', sql)

_from_pattern_re = re.compile(r'\s+FROM\s+(?!\()(\S+)', _pattern_switches)
_into_pattern_re = re.compile(r'\s+INTO\s+(?!\()(\S+)', _pattern_switches)
_update_pattern_re = re.compile(r'\s*UPDATE\s+(?!\()(\S+)', _pattern_switches)
_table_pattern_re = re.compile(r'\s+TABLE\s+(?!\()(\S+)', _pattern_switches)
_call_pattern_re = re.compile(r'\s*CALL\s+(?!\()(\w+)', _pattern_switches)
_show_pattern_re = re.compile(r'\s*SHOW\s+(.*)', _pattern_switches)
_set_pattern_re = re.compile(r'\s*SET\s+(.*?)\W+.*', _pattern_switches)
_exec_pattern_re = re.compile(r'\s*EXEC\s+(?!\()(\w+)', _pattern_switches)
_execute_pattern_re = re.compile(r'\s*EXECUTE\s+(?!\()(\w+)', _pattern_switches)
_alter_pattern_re = re.compile(r'\s*ALTER\s+(?!\()(\w+)', _pattern_switches)

_re_table = {
    u'select': _from_pattern_re,
    u'delete': _from_pattern_re,
    u'insert': _into_pattern_re,
    u'update': _update_pattern_re,
    u'create': _table_pattern_re,
    u'drop': _table_pattern_re,
    u'call': _call_pattern_re,
    u'show': _show_pattern_re,
    u'set': _set_pattern_re,
    u'alter': _alter_pattern_re,
    u'exec': _exec_pattern_re,
    u'execute': _execute_pattern_re,
}

def _parse_operation(sql):
    try:
        # Remove non-word chars from the beginning
        first_word = _word_pattern_re.sub(r'\1', sql)
    except:
        return None

    operation = _extract_identifier(first_word)

    return operation if operation in _re_table.keys() else None

def _parse_table(sql, regex):
    try:
        table = regex.findall(sql)[0]
    except:
        return None

    return _extract_identifier(table)

def _parse_sql_statement_v2(sql):
    internal_metric('Supportability/DatabaseUtils/Parse/Bytes', len(sql))

    sql = _remove_comments(sql)

    operation = _parse_operation(sql)
    if operation is None:
        return (None, None)

    table = _parse_table(sql, _re_table[operation])

    return (table, operation) if table else (None, None)

@internal_trace('Supportability/DatabaseUtils/Calls/parse_sql_statement')
def _parse_sql_statement(sql):
    if _settings.debug.sql_parsing_mechanism == 'regex':
        return _parse_sql_statement_v2(sql)
    else:
        return _parse_sql_statement_v1(sql)

def parsed_sql(name, sql):
    entry = sql_properties_cache.fetch(sql)

    if entry.parsed is not None:
        return entry.parsed

    # We need to operate on SQL which has had IN clause
    # collapsed as SQL parser performs really badly on very
    # big SQL and the IN clause is usually the cause of
    # that.

    # XXX This does mean we are doing obfuscation even if
    # we do not need to. Makes things much quicker though
    # so likely offsets overall performance.

    sql_collapsed = obfuscated_sql(name, sql, collapsed=True)

    entry_collapsed = None

    if sql != sql_collapsed:
        entry_collapsed = sql_properties_cache.fetch(sql_collapsed)

        if entry_collapsed.parsed is not None:
            return entry_collapsed.parsed

    try:
        table, operation = _parse_sql_statement(sql_collapsed)
    except:
        table = None
        operation = None

    entry.parsed = (table, operation)

    if entry_collapsed:
        entry_collapsed.parsed = (table, operation)

    return table, operation

_explain_plan_command = {
    'MySQLdb': 'EXPLAIN',
    'postgresql.interface.proboscis.dbapi2': 'EXPLAIN',
    'psycopg2': 'EXPLAIN',
    'sqlite3.dbapi2': 'EXPLAIN QUERY PLAN',
}

@internal_trace('Supportability/DatabaseUtils/Calls/explain_plan')
def explain_plan(dbapi, sql, connect_params, cursor_params, execute_params):
    name = dbapi and dbapi.__name__ or None

    if name is None:
        return None

    if connect_params is None:
        return None
    if cursor_params is None:
        return None
    if execute_params is None:
        return None

    query = None

    command = _explain_plan_command.get(name)

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
