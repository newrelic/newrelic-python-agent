import pymysql

import pwd
import os

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

USER = pwd.getpwuid(os.getuid()).pw_name

DATABASE_NAME = os.environ.get('TDDIUM_DB_MYSQL_NAME', USER)
DATABASE_USER = os.environ.get('TDDIUM_DB_MYSQL_USER', USER)
DATABASE_PASSWORD = os.environ.get('TDDIUM_DB_MYSQL_PASSWORD', '')
DATABASE_HOST = os.environ.get('TDDIUM_DB_MYSQL_HOST', 'localhost')
DATABASE_PORT = int(os.environ.get('TDDIUM_DB_MYSQL_PORT', '3306'))

_test_execute_via_cursor_scoped_metrics = [
        ('Function/pymysql:Connect', 1),
        ('Function/pymysql.connections:Connection.__enter__', 1),
        ('Function/pymysql.connections:Connection.__exit__', 1),
        ('Database/database_pymysql/select', 1),
        ('Database/database_pymysql/insert', 1),
        ('Database/database_pymysql/update', 1),
        ('Database/database_pymysql/delete', 1),
        ('Database/other/sql', 6)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 10),
        ('Database/allOther', 10),
        ('Database/select', 1),
        ('Database/database_pymysql/select', 1),
        ('Database/insert', 1),
        ('Database/database_pymysql/insert', 1),
        ('Database/update', 1),
        ('Database/database_pymysql/update', 1),
        ('Database/delete', 1),
        ('Database/database_pymysql/delete', 1),
        ('Database/other', 6),
        ('Database/other/sql', 6)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = pymysql.connect(db=DATABASE_NAME, user=DATABASE_USER,
            passwd=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)
    
    with connection as cursor:
        cursor.execute("""drop table if exists database_pymysql""")

        cursor.execute("""create table database_pymysql """
               """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_pymysql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_pymysql""")

        for row in cursor: pass

        cursor.execute("""update database_pymysql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_pymysql where a=2""")

    connection.commit()
    connection.rollback()
    connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/pymysql:Connect', 1),
        ('Function/pymysql.connections:Connection.__enter__', 1),
        ('Function/pymysql.connections:Connection.__exit__', 1),
        ('Database/other/sql', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Database/all', 1),
        ('Database/allOther', 1),
        ('Database/other', 1),
        ('Database/other/sql', 1)]

@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        connection = pymysql.connect(db=DATABASE_NAME, user=DATABASE_USER,
                passwd=DATABASE_PASSWORD, host=DATABASE_HOST,
                port=DATABASE_PORT)
        
        with connection as cursor:
            raise RuntimeError('error')
    except RuntimeError:
        pass
