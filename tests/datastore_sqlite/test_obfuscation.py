import pytest

from newrelic.api.background_task import background_task

from testing_support.validators.validate_sql_obfuscation import validate_sql_obfuscation

@pytest.fixture()
def sqlite3_cursor():
    import sqlite3

    with sqlite3.connect(':memory:') as connection:
        cursor = connection.cursor()
        cursor.execute('drop table if exists a')
        cursor.execute('create table a (b, c)')
        cursor.executemany('insert into a values (?, ?)',
                [(1, 1), (2, 2), (3, 3)])

        yield cursor


_quoting_style_tests = [
    ('SELECT * FROM a WHERE b="c"', 'SELECT * FROM a WHERE b=?'),
    ("SELECT * FROM a WHERE b='c'", 'SELECT * FROM a WHERE b=?'),
]


@pytest.mark.parametrize('sql,obfuscated', _quoting_style_tests)
def test_quoting_styles(sqlite3_cursor, sql, obfuscated):

    @validate_sql_obfuscation([obfuscated])
    @background_task()
    def test():
        sqlite3_cursor.execute(sql)

    test()


_parameter_tests = [
    ('INSERT INTO a VALUES (:1, :2)', 'INSERT INTO a VALUES (:1, :2)'),
    ('INSERT INTO a VALUES (?, ?)', 'INSERT INTO a VALUES (?, ?)'),
]


@pytest.mark.parametrize('sql,obfuscated', _parameter_tests)
def test_parameters(sqlite3_cursor, sql, obfuscated):

    @validate_sql_obfuscation([obfuscated])
    @background_task()
    def test():
        sqlite3_cursor.executemany(sql,
                [('hello', 'world'), ('love', 'python')])

    test()
