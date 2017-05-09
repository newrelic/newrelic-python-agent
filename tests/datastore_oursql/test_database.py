import oursql

from testing_support.fixtures import (validate_transaction_metrics,
            validate_database_trace_inputs)

from testing_support.settings import mysql_settings

from newrelic.api.background_task import background_task

DB_SETTINGS = mysql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/oursql:Connection', 1),
        ('Function/oursql:Connection.__enter__', 1),
        ('Function/oursql:Connection.__exit__', 1),
        ('Datastore/statement/MySQL/datastore_oursql/select', 2),
        ('Datastore/statement/MySQL/datastore_oursql/insert', 1),
        ('Datastore/statement/MySQL/datastore_oursql/update', 1),
        ('Datastore/statement/MySQL/datastore_oursql/delete', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/MySQL/all', 12),
        ('Datastore/MySQL/allOther', 12),
        ('Datastore/operation/MySQL/select', 2),
        ('Datastore/statement/MySQL/datastore_oursql/select', 2),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_oursql/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_oursql/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_oursql/delete', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():

    connection = oursql.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    with connection as cursor:
        cursor.execute("""drop table if exists datastore_oursql""")

        cursor.execute("""create table datastore_oursql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_oursql values (?, ?, ?)""",
                [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_oursql""")

        # The oursql cursor execute() method takes a non DBAPI2
        # argument to disable parameter interpolation. Also
        # changes other behaviour and actually results in a
        # speedup in execution because the default way creates a
        # prepared statement every time and then throws it away.

        cursor.execute("""select * from datastore_oursql""", plain_query=True)

        for row in cursor: pass

        cursor.execute("""update datastore_oursql set a=?, b=?, c=? """
                """where a=?""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_oursql where a=2""")

    connection.commit()
    connection.rollback()
    connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/oursql:Connection', 1),
        ('Function/oursql:Connection.__enter__', 1),
        ('Function/oursql:Connection.__exit__', 1),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/MySQL/all', 2),
        ('Datastore/MySQL/allOther', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():

    try:
        connection = oursql.connect(db=DB_SETTINGS['name'],
                user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
                host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

        with connection as cursor:
            raise RuntimeError('error')
    except RuntimeError:
        pass
