import mysql.connector

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from testing_support.db_settings import mysql_settings
from newrelic.api.background_task import background_task

DB_SETTINGS = mysql_settings()
DB_SETTINGS = DB_SETTINGS[0]

_test_execute_via_cursor_scoped_metrics = [
        ('Function/mysql.connector:connect', 1),
        ('Datastore/statement/MySQL/datastore_mysql/select', 1),
        ('Datastore/statement/MySQL/datastore_mysql/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysql/update', 1),
        ('Datastore/statement/MySQL/datastore_mysql/delete', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 13),
        ('Datastore/allOther', 13),
        ('Datastore/MySQL/all', 13),
        ('Datastore/MySQL/allOther', 13),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_mysql/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysql/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_mysql/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_mysql/delete', 1),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/call', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_execute_via_cursor():

    connection = mysql.connector.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    cursor = connection.cursor()

    cursor.execute("""drop table if exists datastore_mysql""")

    cursor.execute("""create table datastore_mysql """
            """(a integer, b real, c text)""")

    cursor.executemany("""insert into datastore_mysql """
            """values (%(a)s, %(b)s, %(c)s)""", [dict(a=1, b=1.0, c='1.0'),
            dict(a=2, b=2.2, c='2.2'), dict(a=3, b=3.3, c='3.3')])

    cursor.execute("""select * from datastore_mysql""")

    for row in cursor: pass

    cursor.execute("""update datastore_mysql set a=%(a)s, b=%(b)s, """
            """c=%(c)s where a=%(old_a)s""", dict(a=4, b=4.0,
            c='4.0', old_a=1))

    cursor.execute("""delete from datastore_mysql where a=2""")

    cursor.execute("""drop procedure if exists hello""")
    cursor.execute("""CREATE PROCEDURE hello()
                      BEGIN
                        SELECT 'Hello World!';
                      END""")

    cursor.callproc("hello")

    connection.commit()
    connection.rollback()
    connection.commit()

_test_connect_using_alias_scoped_metrics = [
        ('Function/mysql.connector:connect', 1),
        ('Datastore/statement/MySQL/datastore_mysql/select', 1),
        ('Datastore/statement/MySQL/datastore_mysql/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysql/update', 1),
        ('Datastore/statement/MySQL/datastore_mysql/delete', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

_test_connect_using_alias_rollup_metrics = [
        ('Datastore/all', 13),
        ('Datastore/allOther', 13),
        ('Datastore/MySQL/all', 13),
        ('Datastore/MySQL/allOther', 13),
        ('Datastore/operation/MySQL/select', 1),
        ('Datastore/statement/MySQL/datastore_mysql/select', 1),
        ('Datastore/operation/MySQL/insert', 1),
        ('Datastore/statement/MySQL/datastore_mysql/insert', 1),
        ('Datastore/operation/MySQL/update', 1),
        ('Datastore/statement/MySQL/datastore_mysql/update', 1),
        ('Datastore/operation/MySQL/delete', 1),
        ('Datastore/statement/MySQL/datastore_mysql/delete', 1),
        ('Datastore/statement/MySQL/hello/call', 1),
        ('Datastore/operation/MySQL/call', 1),
        ('Datastore/operation/MySQL/drop', 2),
        ('Datastore/operation/MySQL/create', 2),
        ('Datastore/operation/MySQL/commit', 2),
        ('Datastore/operation/MySQL/rollback', 1)]

@validate_transaction_metrics('test_database:test_connect_using_alias',
        scoped_metrics=_test_connect_using_alias_scoped_metrics,
        rollup_metrics=_test_connect_using_alias_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_connect_using_alias():

    connection = mysql.connector.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])

    cursor = connection.cursor()

    cursor.execute("""drop table if exists datastore_mysql""")

    cursor.execute("""create table datastore_mysql """
            """(a integer, b real, c text)""")

    cursor.executemany("""insert into datastore_mysql """
            """values (%(a)s, %(b)s, %(c)s)""", [dict(a=1, b=1.0, c='1.0'),
            dict(a=2, b=2.2, c='2.2'), dict(a=3, b=3.3, c='3.3')])

    cursor.execute("""select * from datastore_mysql""")

    for row in cursor: pass

    cursor.execute("""update datastore_mysql set a=%(a)s, b=%(b)s, """
            """c=%(c)s where a=%(old_a)s""", dict(a=4, b=4.0,
            c='4.0', old_a=1))

    cursor.execute("""delete from datastore_mysql where a=2""")

    cursor.execute("""drop procedure if exists hello""")
    cursor.execute("""CREATE PROCEDURE hello()
                      BEGIN
                        SELECT 'Hello World!';
                      END""")

    cursor.callproc("hello")

    connection.commit()
    connection.rollback()
    connection.commit()
