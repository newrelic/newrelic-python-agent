import mysql.connector

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
        ('Function/mysql.connector:connect', 1),
        ('Database/database_mysql/select', 1),
        ('Database/database_mysql/insert', 1),
        ('Database/database_mysql/update', 1),
        ('Database/database_mysql/delete', 1),
        ('Database/other/sql', 5)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 9),
        ('Database/allOther', 9),
        ('Database/select', 1),
        ('Database/database_mysql/select', 1),
        ('Database/insert', 1),
        ('Database/database_mysql/insert', 1),
        ('Database/update', 1),
        ('Database/database_mysql/update', 1),
        ('Database/delete', 1),
        ('Database/database_mysql/delete', 1),
        ('Database/other', 5),
        ('Database/other/sql', 5)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=dict)
@background_task()
def test_execute_via_cursor():
    connection = mysql.connector.connect(db=DATABASE_NAME, user=DATABASE_USER,
            passwd=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)

    cursor = connection.cursor()

    cursor.execute("""drop table if exists database_mysql""")

    cursor.execute("""create table database_mysql """
            """(a integer, b real, c text)""")

    cursor.executemany("""insert into database_mysql """
            """values (%(a)s, %(b)s, %(c)s)""", [dict(a=1, b=1.0, c='1.0'),
            dict(a=2, b=2.2, c='2.2'), dict(a=3, b=3.3, c='3.3')])

    cursor.execute("""select * from database_mysql""")

    for row in cursor: pass

    cursor.execute("""update database_mysql set a=%(a)s, b=%(b)s, """
            """c=%(c)s where a=%(old_a)s""", dict(a=4, b=4.0,
            c='4.0', old_a=1))

    cursor.execute("""delete from database_mysql where a=2""")

    connection.commit()
    connection.rollback()
    connection.commit()
