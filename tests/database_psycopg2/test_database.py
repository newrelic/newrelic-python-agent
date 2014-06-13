import psycopg2
import psycopg2.extensions
import psycopg2.extras

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import postgresql_settings

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/psycopg2:connect', 1),
        ('Function/psycopg2._psycopg:connection.__enter__', 1),
        ('Function/psycopg2._psycopg:connection.__exit__', 1),
        ('Database/database_psycopg2/select', 1),
        ('Database/database_psycopg2/insert', 1),
        ('Database/database_psycopg2/update', 1),
        ('Database/database_psycopg2/delete', 1),
        ('Database/other/sql', 8)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 13),
        ('Database/allOther', 13),
        ('Database/select', 1),
        ('Database/database_psycopg2/select', 1),
        ('Database/insert', 1),
        ('Database/database_psycopg2/insert', 1),
        ('Database/update', 1),
        ('Database/database_psycopg2/update', 1),
        ('Database/delete', 1),
        ('Database/database_psycopg2/delete', 1),
        ('Database/other', 8),
        ('Database/other/sql', 8)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        cursor = connection.cursor()

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cursor)

        cursor.execute("""drop table if exists database_psycopg2""")

        cursor.execute("""create table database_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_psycopg2""")

        for row in cursor:
            assert isinstance(row, tuple)

        cursor.execute("""update database_psycopg2 set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_psycopg2 where a=2""")

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()

@validate_transaction_metrics('test_database:test_execute_via_cursor_dict',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cursor)

        cursor.execute("""drop table if exists database_psycopg2""")

        cursor.execute("""create table database_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_psycopg2""")

        for row in cursor:
            assert isinstance(row, dict)

        cursor.execute("""update database_psycopg2 set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_psycopg2 where a=2""")

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/psycopg2:connect', 1),
        ('Function/psycopg2._psycopg:connection.__enter__', 1),
        ('Function/psycopg2._psycopg:connection.__exit__', 1),
        ('Database/other/sql', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Database/all', 2),
        ('Database/allOther', 2),
        ('Database/other', 1),
        ('Database/other/sql', 1)]

@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        with psycopg2.connect(
                database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
                password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
                port=DB_SETTINGS['port']) as connection:

            raise RuntimeError('error')
    except RuntimeError:
        pass
