import sqlite3 as database
import os

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DATABASE_DIR = os.environ.get('TOX_ENVDIR', '.')
DATABASE_NAME = os.path.join(DATABASE_DIR, 'database.db')

_test_execute_via_cursor_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Database/database_sqlite/select', 1),
        ('Database/database_sqlite/insert', 1),
        ('Database/database_sqlite/update', 1),
        ('Database/database_sqlite/delete', 1),
        ('Database/other/sql', 5)]

_test_execute_via_cursor_rollup_metrics = [
        ('Database/all', 9),
        ('Database/allOther', 9),
        ('Database/select', 1),
        ('Database/database_sqlite/select', 1),
        ('Database/insert', 1),
        ('Database/database_sqlite/insert', 1),
        ('Database/update', 1),
        ('Database/database_sqlite/update', 1),
        ('Database/delete', 1),
        ('Database/database_sqlite/delete', 1),
        ('Database/other', 5),
        ('Database/other/sql', 5)]

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=tuple)
@background_task()
def test_execute_via_cursor():
    with database.connect(DATABASE_NAME) as connection:
        cursor = connection.cursor()

        cursor.execute("""drop table if exists database_sqlite""")

        cursor.execute("""create table database_sqlite (a, b, c)""")

        cursor.executemany("""insert into database_sqlite values (?, ?, ?)""",
                [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_sqlite""")

        for row in cursor: pass

        cursor.execute("""update database_sqlite set a=?, b=?, """
                """c=? where a=?""", (4, 4.0, '4.0', 1))

        script = """delete from database_sqlite where a = 2;"""
        cursor.executescript(script)

        connection.commit()
        connection.rollback()
        connection.commit()

_test_execute_via_connection_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Database/database_sqlite/select', 1),
        ('Database/database_sqlite/insert', 1),
        ('Database/database_sqlite/update', 1),
        ('Database/database_sqlite/delete', 1),
        ('Database/other/sql', 5)]

_test_execute_via_connection_rollup_metrics = [
        ('Database/all', 9),
        ('Database/allOther', 9),
        ('Database/select', 1),
        ('Database/database_sqlite/select', 1),
        ('Database/insert', 1),
        ('Database/database_sqlite/insert', 1),
        ('Database/update', 1),
        ('Database/database_sqlite/update', 1),
        ('Database/delete', 1),
        ('Database/database_sqlite/delete', 1),
        ('Database/other', 5),
        ('Database/other/sql', 5)]

@validate_transaction_metrics('test_database:test_execute_via_connection',
        scoped_metrics=_test_execute_via_connection_scoped_metrics,
        rollup_metrics=_test_execute_via_connection_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(execute_params_type=tuple)
@background_task()
def test_execute_via_connection():
    with database.connect(DATABASE_NAME) as connection:
        connection.execute("""drop table if exists database_sqlite""")

        connection.execute("""create table database_sqlite (a, b, c)""")

        connection.executemany("""insert into database_sqlite values """
                """(?, ?, ?)""", [(1, 1.0, '1.0'), (2, 2.2, '2.2'),
                (3, 3.3, '3.3')])

        connection.execute("""select * from database_sqlite""")

        connection.execute("""update database_sqlite set a=?, b=?, """
                """c=? where a=?""", (4, 4.0, '4.0', 1))

        script = """delete from database_sqlite where a = 2;"""
        connection.executescript(script)

        connection.commit()
        connection.rollback()
        connection.commit()
