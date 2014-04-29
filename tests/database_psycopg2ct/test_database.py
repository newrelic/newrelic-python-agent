import psycopg2ct
import psycopg2ct.extensions

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import postgresql_settings

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/psycopg2ct:connect', 1),
        ('Database/database_psycopg2ct/select', 1),
        ('Database/database_psycopg2ct/insert', 1),
        ('Database/database_psycopg2ct/update', 1),
        ('Database/database_psycopg2ct/delete', 1),
        ('Database/other/sql', 7)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 12),
        ('Database/allOther', 12),
        ('Database/select', 1),
        ('Database/database_psycopg2ct/select', 1),
        ('Database/insert', 1),
        ('Database/database_psycopg2ct/insert', 1),
        ('Database/update', 1),
        ('Database/database_psycopg2ct/update', 1),
        ('Database/delete', 1),
        ('Database/database_psycopg2ct/delete', 1),
        ('Database/other', 7),
        ('Database/other/sql', 7)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = psycopg2ct.connect(database=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], password=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    cursor = connection.cursor()

    psycopg2ct.extensions.register_type(psycopg2ct.extensions.UNICODE)
    psycopg2ct.extensions.register_type(psycopg2ct.extensions.UNICODE, connection)
    psycopg2ct.extensions.register_type(psycopg2ct.extensions.UNICODE, cursor)

    cursor.execute("""drop table if exists database_psycopg2ct""")

    cursor.execute("""create table database_psycopg2ct """
            """(a integer, b real, c text)""")

    cursor.executemany("""insert into database_psycopg2ct """
            """values (%s, %s, %s)""", [(1, 1.0, '1.0'), (2, 2.2, '2.2'),
            (3, 3.3, '3.3')])

    cursor.execute("""select * from database_psycopg2ct""")

    for row in cursor: pass

    cursor.execute("""update database_psycopg2ct set a=%s, b=%s, c=%s """
            """where a=%s""", (4, 4.0, '4.0', 1))

    cursor.execute("""delete from database_psycopg2ct where a=2""")

    connection.commit()

    cursor.callproc('now')
    cursor.callproc('pg_sleep', (0.25,))

    connection.rollback()
    connection.commit()
