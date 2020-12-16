import os
import psycopg2
import psycopg2.extras

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)
from utils import DB_SETTINGS

from newrelic.api.background_task import background_task


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

        psycopg2.extras.register_json(connection, loads=lambda x: x)
        psycopg2.extras.register_json(cursor, loads=lambda x: x)

@validate_transaction_metrics('test_register:test_register_range',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_range():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        type_name = "floatrange_" + str(os.getpid())

        create_sql = ('CREATE TYPE %s AS RANGE (' % type_name +
                      'subtype = float8,'
                      'subtype_diff = float8mi)')

        cursor = connection.cursor()

        cursor.execute("DROP TYPE if exists %s" % type_name)
        cursor.execute(create_sql)

        psycopg2.extras.register_range(type_name,
                psycopg2.extras.NumericRange, connection)

        cursor.execute("DROP TYPE if exists %s" % type_name)
        cursor.execute(create_sql)

        psycopg2.extras.register_range(type_name,
                psycopg2.extras.NumericRange, cursor)

        cursor.execute("DROP TYPE if exists %s" % type_name)
