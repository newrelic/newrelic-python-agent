import postgresql.interface.proboscis.dbapi2

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import postgresql_settings

from newrelic.agent import background_task

DB_SETTINGS = postgresql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/postgresql.interface.proboscis.dbapi2:connect', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/select', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/insert', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/update', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/delete', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/Postgres/all', 12),
        ('Datastore/Postgres/allOther', 12),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/insert', 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/update', 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/datastore_proboscis/delete', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/call', 2),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_execute_via_cursor():
    connection = postgresql.interface.proboscis.dbapi2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    cursor = connection.cursor()

    cursor.execute("""drop table if exists datastore_proboscis""")

    cursor.execute("""create table datastore_proboscis """
           """(a integer, b real, c text)""")

    cursor.executemany("""insert into datastore_proboscis """
            """values (%(a)s, %(b)s, %(c)s)""", [dict(a=1, b=1.0, c='1.0'),
            dict(a=2, b=2.2, c='2.2'), dict(a=3, b=3.3, c='3.3')])

    cursor.execute("""select * from datastore_proboscis""")

    for row in cursor: pass

    cursor.execute("""update datastore_proboscis set a=%(a)s, """
            """b=%(b)s, c=%(c)s where a=%(old_a)s""", dict(a=4, b=4.0,
            c='4.0', old_a=1))

    cursor.execute("""delete from datastore_proboscis where a=2""")

    connection.commit()

    cursor.callproc('now', ())
    cursor.callproc('pg_sleep', (0.25,))

    connection.rollback()
    connection.commit()
