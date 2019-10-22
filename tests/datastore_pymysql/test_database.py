import pymysql

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import mysql_settings

from newrelic.api.background_task import background_task

DB_SETTINGS = mysql_settings()


def execute_db_calls_with_cursor(cursor):
    cursor.execute("""drop table if exists datastore_pymysql""")

    cursor.execute("""create table datastore_pymysql """
           """(a integer, b real, c text)""")

    cursor.executemany("""insert into datastore_pymysql """
            """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
            (2, 2.2, '2.2'), (3, 3.3, '3.3')])

    cursor.execute("""select * from datastore_pymysql""")

    for row in cursor: pass

    cursor.execute("""update datastore_pymysql set a=%s, b=%s, """
            """c=%s where a=%s""", (4, 4.0, '4.0', 1))

    cursor.execute("""delete from datastore_pymysql where a=2""")
    cursor.execute("""drop procedure if exists hello""")
    cursor.execute("""CREATE PROCEDURE hello()
                      BEGIN
                        SELECT 'Hello World!';
                      END""")

    cursor.callproc("hello")


_test_execute_via_cursor_scoped_metrics = [
        ('Function/pymysql:Connect', 1),
        ('Function/pymysql.connections:Connection.__enter__', 1),
        ('Function/pymysql.connections:Connection.__exit__', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/select', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/insert', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/update', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/delete', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 14),
        ('Datastore/allOther', 14),
        ('Datastore/MySQL/all', 14),
        ('Datastore/MySQL/allOther', 14),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/delete', 1),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/call', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = pymysql.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    with connection as cursor:
        execute_db_calls_with_cursor(cursor)

    connection.commit()
    connection.rollback()
    connection.commit()


_test_execute_via_cursor_context_mangaer_scoped_metrics = [
        ('Function/pymysql:Connect', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/select', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/insert', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/update', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/delete', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_context_mangaer_rollup_metrics = [
        ('Datastore/all', 13),
        ('Datastore/allOther', 13),
        ('Datastore/MySQL/all', 13),
        ('Datastore/MySQL/allOther', 13),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_pymysql/delete', 1),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/call', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]


@validate_transaction_metrics(
        'test_database:test_execute_via_cursor_context_manager',
        scoped_metrics=_test_execute_via_cursor_context_mangaer_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_context_mangaer_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_context_manager():
    connection = pymysql.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    with connection.cursor() as cursor:
        execute_db_calls_with_cursor(cursor)

    connection.commit()
    connection.rollback()
    connection.commit()


_test_rollback_on_exception_scoped_metrics = [
        ('Function/pymysql:Connect', 1),
        ('Function/pymysql.connections:Connection.__enter__', 1),
        ('Function/pymysql.connections:Connection.__exit__', 1),
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
        connection = pymysql.connect(db=DB_SETTINGS['name'],
                user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
                host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

        with connection as cursor:
            raise RuntimeError('error')
    except RuntimeError:
        pass
