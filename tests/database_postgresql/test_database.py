import postgresql.driver.dbapi20

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import postgresql_settings

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/postgresql.driver.dbapi20:connect', 1),
        ('Database/database_postgresql/select', 1),
        ('Database/database_postgresql/insert', 1),
        ('Database/database_postgresql/update', 1),
        ('Database/database_postgresql/delete', 1),
        ('Database/other/sql', 7)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 11),
        ('Database/allOther', 11),
        ('Database/select', 1),
        ('Database/database_postgresql/select', 1),
        ('Database/insert', 1),
        ('Database/database_postgresql/insert', 1),
        ('Database/update', 1),
        ('Database/database_postgresql/update', 1),
        ('Database/delete', 1),
        ('Database/database_postgresql/delete', 1),
        ('Database/other', 7),
        ('Database/other/sql', 7)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=tuple)
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
