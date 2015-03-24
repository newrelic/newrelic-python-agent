import MySQLdb

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.settings import mysql_settings

from newrelic.agent import background_task

DB_SETTINGS = mysql_settings()

_test_execute_via_cursor_scoped_metrics = [
        ('Function/MySQLdb:Connect', 1),
        ('Function/MySQLdb.connections:Connection.__enter__', 1),
        ('Function/MySQLdb.connections:Connection.__exit__', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/select', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/update', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/delete', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/show', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/MySQL/all', 12),
        ('Datastore/MySQL/allOther', 12),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/delete', 1),
        ('Datastore/operation/MySQL/show', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(tuple)
@background_task()
def test_execute_via_cursor():
    connection = MySQLdb.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    with connection as cursor:
        cursor.execute("""drop table if exists datastore_mysqldb""")

        cursor.execute("""create table datastore_mysqldb """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_mysqldb """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_mysqldb""")

        for row in cursor: pass

        cursor.execute("""update datastore_mysqldb set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_mysqldb where a=2""")

        cursor.execute("""show authors""")

    connection.commit()
    connection.rollback()
    connection.commit()

_test_connect_using_alias_scoped_metrics = [
        ('Function/MySQLdb:Connect', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/select', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/update', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/delete', 1),
        ('Datastore/operation/MySQL/show', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_connect_using_alias_rollup_metrics = [
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/MySQL/all', 12),
        ('Datastore/MySQL/allOther', 12),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_mysqldb/delete', 1),
        ('Datastore/operation/MySQL/show', 1),
        ('Datastore/operation/MySQL/drop', 1),
        ('Datastore/operation/MySQL/create', 1),
        ('Datastore/operation/MySQL/commit', 3),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_connect_using_alias',
        scoped_metrics=_test_connect_using_alias_scoped_metrics,
        rollup_metrics=_test_connect_using_alias_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(tuple)
@background_task()
def test_connect_using_alias():
    connection = MySQLdb.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    with connection as cursor:
        cursor.execute("""drop table if exists datastore_mysqldb""")

        cursor.execute("""create table datastore_mysqldb """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_mysqldb """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_mysqldb""")

        for row in cursor: pass

        cursor.execute("""update datastore_mysqldb set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_mysqldb where a=2""")

        cursor.execute("""show authors""")

    connection.commit()
    connection.rollback()
    connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/MySQLdb:Connect', 1),
        ('Function/MySQLdb.connections:Connection.__enter__', 1),
        ('Function/MySQLdb.connections:Connection.__exit__', 1),
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
        with MySQLdb.connect(
            db=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            passwd=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

            raise RuntimeError('error')
    except RuntimeError:
        pass
