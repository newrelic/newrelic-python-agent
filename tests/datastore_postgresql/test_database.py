import postgresql.driver.dbapi20

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import postgresql_settings

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/postgresql.driver.pq3:Connection.__enter__', 1),
        ('Function/postgresql.driver.pq3:Connection.__exit__', 1),
        ('Datastore/statement/Postgres/database_postgresql/select', 1),
        ('Datastore/statement/Postgres/database_postgresql/insert', 1),
        ('Datastore/statement/Postgres/database_postgresql/update', 1),
        ('Datastore/statement/Postgres/database_postgresql/delete', 1),
        ('Datastore/statement/Postgres/other/other', 8)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 13),
        ('Datastore/allOther', 13),
        ('Datastore/Postgres/all', 13),
        ('Datastore/Postgres/allOther', 13),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/database_postgresql/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/database_postgresql/insert', 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/database_postgresql/update', 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/database_postgresql/delete', 1),
        ('Datastore/instance/Postgres/localhost/database_postgresql', 4),
        ('Datastore/operation/Postgres/other', 8),
        ('Datastore/statement/Postgres/other/other', 8)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    with postgresql.driver.dbapi20.connect(database=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], password=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port']) as connection:

        cursor = connection.cursor()

        cursor.execute("""drop table if exists database_postgresql""")

        cursor.execute("""create table database_postgresql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_postgresql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_postgresql""")

        for row in cursor: pass

        cursor.execute("""update database_postgresql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_postgresql where a=2""")

        connection.commit()

        cursor.callproc('now', ())
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/postgresql.driver.pq3:Connection.__enter__', 1),
        ('Function/postgresql.driver.pq3:Connection.__exit__', 1),
        ('Datastore/statement/Postgres/other/other', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Postgres/all', 2),
        ('Datastore/Postgres/allOther', 2)]

@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        with postgresql.driver.dbapi20.connect(database=DB_SETTINGS['name'],
                user=DB_SETTINGS['user'], password=DB_SETTINGS['password'],
                host=DB_SETTINGS['host'], port=DB_SETTINGS['port']) as connection:

            raise RuntimeError('error')
    except RuntimeError:
        pass
