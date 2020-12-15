import pymysql

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.db_settings import mysql_settings

from newrelic.api.background_task import background_task

DB_SETTINGS = mysql_settings()[0]
TABLE_NAME = "datastore_pymysql_" + DB_SETTINGS["namespace"]
PROCEDURE_NAME = "hello_" + DB_SETTINGS["namespace"]


def execute_db_calls_with_cursor(cursor):
    cursor.execute("""drop table if exists %s""" % TABLE_NAME)

    cursor.execute("""create table %s """ % TABLE_NAME +
           """(a integer, b real, c text)""")

    cursor.executemany("""insert into %s """ % TABLE_NAME +
            """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
            (2, 2.2, '2.2'), (3, 3.3, '3.3')])

    cursor.execute("""select * from %s""" % TABLE_NAME)

    for row in cursor: pass

    cursor.execute("""update %s""" % TABLE_NAME + """ set a=%s, b=%s, """
            """c=%s where a=%s""", (4, 4.0, '4.0', 1))

    cursor.execute("""delete from %s where a=2""" % TABLE_NAME)
    cursor.execute("""drop procedure if exists %s""" % PROCEDURE_NAME)
    cursor.execute("""CREATE PROCEDURE %s()
                      BEGIN
                        SELECT 'Hello World!';
                      END""" % PROCEDURE_NAME)

    cursor.callproc(PROCEDURE_NAME)


_test_execute_via_cursor_scoped_metrics = [
        ('Function/pymysql:Connect', 1),
        ('Function/pymysql.connections:Connection.__enter__', 1),
        ('Function/pymysql.connections:Connection.__exit__', 1),
        ('Datastore/statement/MySQL/%s/select' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/insert' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/update' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/delete' % TABLE_NAME, 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/statement/MySQL/%s/call' % PROCEDURE_NAME, 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 14),
        ('Datastore/allOther', 14),
        ('Datastore/MySQL/all', 14),
        ('Datastore/MySQL/allOther', 14),
        ('Datastore/statement/MySQL/%s/select' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/insert' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/update' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/delete' % TABLE_NAME, 1),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/%s/call' % PROCEDURE_NAME, 1),
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
        ('Datastore/statement/MySQL/%s/select' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/insert' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/update' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/delete' % TABLE_NAME, 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/statement/MySQL/%s/call' % PROCEDURE_NAME, 1),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_context_mangaer_rollup_metrics = [
        ('Datastore/all', 13),
        ('Datastore/allOther', 13),
        ('Datastore/MySQL/all', 13),
        ('Datastore/MySQL/allOther', 13),
        ('Datastore/statement/MySQL/%s/select' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/insert' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/update' % TABLE_NAME, 1),
        ('Datastore/statement/MySQL/%s/delete' % TABLE_NAME, 1),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/%s/call' % PROCEDURE_NAME, 1),
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
