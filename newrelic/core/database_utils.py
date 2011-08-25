"""Database utilities consists of routines for obfuscating SQL, retrieving
explain plans for SQL etc.

"""

import re

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
# These probably could be combine into one expression but clearer
# if we described them separately.

_float_re = re.compile(r'(\b[0-9]+\.([0-9]+\b)?|\.[0-9]+\b)')
_int_re = re.compile(r'\b\d+\b')

def obfuscate_sql(name, sql):
    """Returns obfuscated version of the sql. The quoting
    convention is determined by looking at the name of the
    database module supplied. Obfuscation consists of replacing
    literal strings, floats and integers.

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

    # Now we want to replace floating point literal values.
    # Need to do this before integers or we will get strange
    # results.

    sql = _float_re.sub('?', sql)

    # Finally replace straight integer values.

    sql = _int_re.sub('?', sql)

    return sql


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
