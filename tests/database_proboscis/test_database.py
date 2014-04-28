import postgresql.interface.proboscis.dbapi2

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import postgresql_settings

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/postgresql.interface.proboscis.dbapi2:connect', 1),
        ('Database/database_proboscis/select', 1),
        ('Database/database_proboscis/insert', 1),
        ('Database/database_proboscis/update', 1),
        ('Database/database_proboscis/delete', 1),
        ('Database/other/sql', 7)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 12),
        ('Database/allOther', 12),
        ('Database/select', 1),
        ('Database/database_proboscis/select', 1),
        ('Database/insert', 1),
        ('Database/database_proboscis/insert', 1),
        ('Database/update', 1),
        ('Database/database_proboscis/update', 1),
        ('Database/delete', 1),
        ('Database/database_proboscis/delete', 1),
        ('Database/other', 7),
        ('Database/other/sql', 7)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=dict)
@background_task()
def test_execute_via_cursor():
    connection = postgresql.interface.proboscis.dbapi2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    cursor = connection.cursor()

    cursor.execute("""drop table if exists database_proboscis""")

    cursor.execute("""create table database_proboscis """
           """(a integer, b real, c text)""")

    cursor.executemany("""insert into database_proboscis """
            """values (%(a)s, %(b)s, %(c)s)""", [dict(a=1, b=1.0, c='1.0'),
            dict(a=2, b=2.2, c='2.2'), dict(a=3, b=3.3, c='3.3')])

    cursor.execute("""select * from database_proboscis""")

    for row in cursor: pass

    cursor.execute("""update database_proboscis set a=%(a)s, """
            """b=%(b)s, c=%(c)s where a=%(old_a)s""", dict(a=4, b=4.0,
            c='4.0', old_a=1))

    cursor.execute("""delete from database_proboscis where a=2""")

    connection.commit()

    cursor.callproc('now', ())
    cursor.callproc('pg_sleep', (0.25,))

    connection.rollback()
    connection.commit()
