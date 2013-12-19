import psycopg2ct
import psycopg2ct.extensions

import pwd
import os

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

USER = pwd.getpwuid(os.getuid()).pw_name

DATABASE_NAME = os.environ.get('TDDIUM_DB_PG_NAME', USER)
DATABASE_USER = os.environ.get('TDDIUM_DB_PG_USER', USER)
DATABASE_PASSWORD = os.environ.get('TDDIUM_DB_PG_PASSWORD')
DATABASE_HOST = os.environ.get('TDDIUM_DB_PG_HOST', 'localhost')
DATABASE_PORT = int(os.environ.get('TDDIUM_DB_PG_PORT', '5432'))

_test_execute_via_cursor_scoped_metrics = [
        ('Function/psycopg2ct:connect', 1),
        ('Database/database_psycopg2ct/select', 1),
        ('Database/database_psycopg2ct/insert', 1),
        ('Database/database_psycopg2ct/update', 1),
        ('Database/database_psycopg2ct/delete', 1),
        ('Database/other/sql', 7)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 11),
        ('Database/allOther', 11),
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
@validate_database_trace_inputs(execute_params_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = psycopg2ct.connect(database=DATABASE_NAME,
            user=DATABASE_USER, password=DATABASE_PASSWORD,
            host=DATABASE_HOST, port=DATABASE_PORT)

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
