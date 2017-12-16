import json
import os
import pytest

from newrelic.core.database_utils import SQLDatabase, SQLStatement


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'sql_obfuscation'))

_parameters_list = ['obfuscated', 'dialects', 'sql', 'malformed',
        'pathological']
_parameters = ','.join(_parameters_list)


def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'sql_obfuscation.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = tuple([test.get(param, None) for param in _parameters_list])
        result.append(values)

    return result


_dbapi2modules = None


def _load_dbapi2modules():

    # TODO: is importing these the right thing to do? or should I just create a
    # dummy db that is either single, double or single+double?

    import sqlite3, mysql.connector as mysql, psycopg2, cx_Oracle  # noqa

    return {
        'sqlite': [sqlite3],
        'mysql': [mysql],
        'postgres': [psycopg2],
        'oracle': [cx_Oracle],
        'cassandra': [],
    }


def get_dbpi2modules(dialects):
    global _dbapi2modules
    if not _dbapi2modules:
        _dbapi2modules = _load_dbapi2modules()

    modules = []

    for dialect in dialects:
        modules_for_dialect = _dbapi2modules.get(dialect)
        modules.extend(modules_for_dialect)

    return modules


@pytest.mark.xfail()
@pytest.mark.parametrize(_parameters, load_tests())
def test_sql_obfuscation(obfuscated, dialects, sql, malformed, pathological):

    dbapi2modules = get_dbpi2modules(dialects)

    for dbapi2module in dbapi2modules:
        database = SQLDatabase(dbapi2module)
        statement = SQLStatement(sql, database)
        actual_obfuscated = statement.obfuscated
        assert actual_obfuscated in obfuscated
