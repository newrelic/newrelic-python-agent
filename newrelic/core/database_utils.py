"""Database utilities consists of routines for obfuscating SQL, retrieving
explain plans for SQL etc.

"""

import re

import newrelic.lib.sqlparse
import newrelic.lib.sqlparse.sql
import newrelic.lib.sqlparse.tokens

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

_int_re = re.compile(r'\b\d+\b')

def obfuscate_sql(name, sql):
    """Returns obfuscated version of the sql. The quoting
    convention is determined by looking at the name of the
    database module supplied. Obfuscation consists of replacing
    literal strings and integers.

    """

    # Substitute quoted strings first. In the case of MySQL it
    # uses back quotes around table names so safe to replace
    # contents of strings using either single of double quotes.
    # For PostgreSQL and other databases, double quotes are used
    # around table names so only replace contents of single
    # quoted strings.

    if name in ['MySQLdb']:
        sql = _any_quotes_re.sub('?', sql)
    else:
        sql = _single_quotes_re.sub('?', sql)

    # Finally replace straight integer values. This will pick
    # up integers by themselves but also as part of floating
    # point numbers. Because of word boundary checks in pattern
    # will not match numbers within identifier names.

    sql = _int_re.sub('?', sql)

    return sql

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

def parsed_sql(sql):
    # FIXME The SqlParser class doesn't cope well with badly
    # formed input data, so need to catch exceptions here.

    try:
        parsed_sql = SqlParser(sql)
        table = parsed_sql.table
        operation = parsed_sql.operation
    except:
        table = None
        operation = None

    return table, operation
    
# XXX The following is no longer used. Kept here for reference for
# time being only.

"""
from newrelic.core.string_normalization import *

def obfuscator(database_type="postgresql"):
    numeric              = DefaultNormalizationRule._replace(match_expression=r'\d+', replacement="?")
    single_quoted_string = DefaultNormalizationRule._replace(match_expression=r"'(.*?[^\\'])??'(?!')", replacement="?")
    double_quoted_string = DefaultNormalizationRule._replace(match_expression=r'"(.*?[^\\"])??"(?!")', replacement="?")

    if database_type == "mysql":
        return SqlObfuscator(numeric, single_quoted_string,
                             double_quoted_string)
    elif database_type == "postgresql":
        return SqlObfuscator(numeric, single_quoted_string)

class SqlObfuscator(Normalizer):
    def obfuscate(self, sql):
        return self.normalize(sql)

# MySQL - `table.name`
# Oracle - "table.name"
# PostgreSQL - "table.name"
# SQLite - "table.name"

NORMALIZER_DEFAULT = 'postgresql'

NORMALIZER_SCHEME = {
  'cx_Oracle' : NORMALIZER_DEFAULT,
  'MySQLdb': 'mysql',
  'postgresql.interface.proboscis.dbapi2': 'postgresql',
  'psycopg2': 'postgresql',
  'pysqlite2.dbapi2': NORMALIZER_DEFAULT,
  'sqlite3.dbapi2': NORMALIZER_DEFAULT,
}

def obfuscate_sql(dbapi, sql):
    name = dbapi and dbapi.__name__ or None
    scheme = NORMALIZER_SCHEME.get(name, NORMALIZER_DEFAULT)
    return obfuscator(scheme).obfuscate(sql)
"""
