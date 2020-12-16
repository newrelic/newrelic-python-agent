import pytest
import psycopg2
from psycopg2 import extensions as ext
from utils import DB_SETTINGS
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.hooks.database_psycopg2 import wrapper_psycopg2_as_string


class TestCompatability(object):
    def as_string(self, giraffe, lion, tiger=None):
        assert isinstance(giraffe, ext.cursor)
        return "PASS"

wrap_function_wrapper(__name__, 'TestCompatability.as_string',
    wrapper_psycopg2_as_string)


@pytest.fixture(scope='module')
def conn():
    conn = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])
    yield conn
    conn.close()


def test_forward_compat_args(conn):
    cursor = conn.cursor()
    query = TestCompatability()
    result = query.as_string(cursor, 'giraffe-nomming-leaves')
    assert result == 'PASS'


def test_forward_compat_kwargs(conn):
    cursor = conn.cursor()
    query = TestCompatability()
    result = query.as_string(cursor, lion='eats tiger', tiger='eats giraffe')
    assert result == 'PASS'
