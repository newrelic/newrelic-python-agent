import decimal
import json

import psycopg2
import psycopg2.extras
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)
from utils import DB_SETTINGS, POSTGRESQL_VERSION

from newrelic.agent import background_task


@pytest.mark.skipif(POSTGRESQL_VERSION < (9, 2),
        reason="JSON data type was introduced in Postgres 9.2")
@validate_transaction_metrics('test_register:test_register_json',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_json():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        cursor = connection.cursor()

        loads = lambda x: json.loads(x, parse_float=decimal.Decimal)
        psycopg2.extras.register_json(connection, loads=loads)
        psycopg2.extras.register_json(cursor, loads=loads)

@pytest.mark.skipif(POSTGRESQL_VERSION < (9, 2),
        reason="Range types were introduced in Postgres 9.2")
@validate_transaction_metrics('test_register:test_register_range',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_range():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        create_sql = ('CREATE TYPE floatrange AS RANGE ('
                      'subtype = float8,'
                      'subtype_diff = float8mi)')

        cursor = connection.cursor()

        cursor.execute("DROP TYPE if exists floatrange")
        cursor.execute(create_sql)

        psycopg2.extras.register_range('floatrange',
                psycopg2.extras.NumericRange, connection)

        cursor.execute("DROP TYPE if exists floatrange")
        cursor.execute(create_sql)

        psycopg2.extras.register_range('floatrange',
                psycopg2.extras.NumericRange, cursor)

        cursor.execute("DROP TYPE if exists floatrange")
