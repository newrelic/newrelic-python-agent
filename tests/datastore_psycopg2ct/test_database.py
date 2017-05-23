import select

import psycopg2ct
import psycopg2ct.extensions

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, validate_transaction_errors,
    validate_transaction_slow_sql_count,
    validate_stats_engine_explain_plan_output_is_none)

from testing_support.settings import postgresql_settings

from newrelic.agent import background_task

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/psycopg2ct:connect', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/delete', 1),
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
        ('Datastore/statement/Postgres/datastore_psycopg2ct/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/insert', 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/update', 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/delete', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/call', 2),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

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

    cursor.execute("""drop table if exists datastore_psycopg2ct""")

    cursor.execute("""create table datastore_psycopg2ct """
            """(a integer, b real, c text)""")

    cursor.executemany("""insert into datastore_psycopg2ct """
            """values (%s, %s, %s)""", [(1, 1.0, '1.0'), (2, 2.2, '2.2'),
            (3, 3.3, '3.3')])

    cursor.execute("""select * from datastore_psycopg2ct""")

    for row in cursor: pass

    cursor.execute("""update datastore_psycopg2ct set a=%s, b=%s, c=%s """
            """where a=%s""", (4, 4.0, '4.0', 1))

    cursor.execute("""delete from datastore_psycopg2ct where a=2""")

    connection.commit()

    cursor.callproc('now')
    cursor.callproc('pg_sleep', (0.25,))

    connection.rollback()
    connection.commit()

_test_async_mode_scoped_metrics = [
        ('Function/psycopg2ct:connect', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/insert', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)]

_test_async_mode_rollup_metrics = [
        ('Datastore/all', 5),
        ('Datastore/allOther', 5),
        ('Datastore/Postgres/all', 5),
        ('Datastore/Postgres/allOther', 5),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2ct/insert', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)]

@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics('test_database:test_async_mode',
        scoped_metrics=_test_async_mode_scoped_metrics,
        rollup_metrics=_test_async_mode_rollup_metrics,
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_async_mode():

    def wait(conn):
        while 1:
            state = conn.poll()
            if state == psycopg2ct.extensions.POLL_OK:
                break
            elif state == psycopg2ct.extensions.POLL_WRITE:
                select.select([], [conn.fileno()], [])
            elif state == psycopg2ct.extensions.POLL_READ:
                select.select([conn.fileno()], [], [])
            else:
                raise psycopg2ct.OperationalError("poll() returned %s" % state)

    async_conn = psycopg2ct.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], async=1
    )
    wait(async_conn)
    async_cur = async_conn.cursor()

    async_cur.execute("""drop table if exists datastore_psycopg2ct""")
    wait(async_cur.connection)

    async_cur.execute("""create table datastore_psycopg2ct """
            """(a integer, b real, c text)""")
    wait(async_cur.connection)

    async_cur.execute("""insert into datastore_psycopg2ct """
        """values (%s, %s, %s)""", (1, 1.0, '1.0'))
    wait(async_cur.connection)

    async_cur.execute("""select * from datastore_psycopg2ct""")
    wait(async_cur.connection)

    for row in async_cur:
        assert isinstance(row, tuple)

    async_conn.close()
