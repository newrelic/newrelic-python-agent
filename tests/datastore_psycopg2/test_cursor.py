import psycopg2
import psycopg2.extensions
import psycopg2.extras

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)
from utils import DB_SETTINGS

from newrelic.agent import background_task, global_settings


settings = global_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/Postgres/all', 12),
        ('Datastore/Postgres/allOther', 12),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/call', 2),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

# The feature flags are expected to be bound and set
# through env vars at the time the test is imported
if 'datastore.instances.r1' in settings.feature_flag:
    _test_execute_via_cursor_scoped_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 12))
    _test_execute_via_cursor_rollup_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 12))

@validate_transaction_metrics('test_cursor:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cursor)

        cursor.execute("""drop table if exists datastore_psycopg2""")

        cursor.execute("""create table datastore_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_psycopg2""")

        for row in cursor:
            assert isinstance(row, tuple)

        cursor.execute("""update datastore_psycopg2 set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_psycopg2 where a=2""")

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()

    finally:
        connection.close()

@validate_transaction_metrics('test_cursor:test_execute_via_cursor_dict',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cursor)

        cursor.execute("""drop table if exists datastore_psycopg2""")

        cursor.execute("""create table datastore_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_psycopg2""")

        for row in cursor:
            assert isinstance(row, dict)

        cursor.execute("""update datastore_psycopg2 set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_psycopg2 where a=2""")

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()

    finally:
        connection.close()
