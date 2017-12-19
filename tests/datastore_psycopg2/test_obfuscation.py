import pytest

from newrelic.api.background_task import background_task

from testing_support.fixtures import validate_sql_obfuscation
from utils import DB_SETTINGS


@pytest.fixture()
def psycopg2_cursor():
    import psycopg2

    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()

        cursor.execute('drop table if exists a')
        cursor.execute('create table a (b text, c text)')
        cursor.executemany('insert into a values (%s, %s)',
                [('1', '1'), ('2', '2'), ('3', '3')])

        yield cursor

    finally:
        connection.close()


_quoting_style_tests = [
    ("SELECT * FROM a WHERE b='2'", 'SELECT * FROM a WHERE b=?'),
    ('SELECT * FROM a WHERE b=$func$2$func$', 'SELECT * FROM a WHERE b=?'),
    ("SELECT * FROM a WHERE b=U&'2'", 'SELECT * FROM a WHERE b=U&?'),
]


@pytest.mark.parametrize('sql,obfuscated', _quoting_style_tests)
def test_quoting_styles(psycopg2_cursor, sql, obfuscated):

    @validate_sql_obfuscation([obfuscated])
    @background_task()
    def test():
        psycopg2_cursor.execute(sql)

    test()
