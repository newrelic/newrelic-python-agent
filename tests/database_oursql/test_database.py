import oursql

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
        ('Function/oursql:Connection', 1),
        ('Database/database_oursql/select', 1),
        ('Database/database_oursql/insert', 1),
        ('Database/database_oursql/update', 1),
        ('Database/database_oursql/delete', 1),
        ('Database/other/sql', 5)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 9),
        ('Database/allOther', 9),
        ('Database/select', 1),
        ('Database/database_oursql/select', 1),
        ('Database/insert', 1),
        ('Database/database_oursql/insert', 1),
        ('Database/update', 1),
        ('Database/database_oursql/update', 1),
        ('Database/delete', 1),
        ('Database/database_oursql/delete', 1),
        ('Database/other', 5),
        ('Database/other/sql', 5)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = oursql.connect(db=DATABASE_NAME, user=DATABASE_USER,
            passwd=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)
    
    with connection as cursor:
        cursor.execute("""drop table if exists database_oursql""")

        cursor.execute("""create table database_oursql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_oursql values (?, ?, ?)""",
                [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_oursql""")

        for row in cursor: pass

        cursor.execute("""update database_oursql set a=?, b=?, c=? """
                """where a=?""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_oursql where a=2""")

    connection.commit()
    connection.rollback()
    connection.commit()
