import sqlite3 as database
import os
import sys

is_pypy = hasattr(sys, 'pypy_version_info')

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

DATABASE_DIR = os.environ.get('TOX_ENVDIR', '.')
#DATABASE_NAME = os.path.join(DATABASE_DIR, 'database.db')
DATABASE_NAME = ':memory:'

_test_execute_via_cursor_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Datastore/statement/SQLite/database_sqlite/select', 1),
        ('Datastore/statement/SQLite/database_sqlite/insert', 1),
        ('Datastore/statement/SQLite/database_sqlite/update', 1),
        ('Datastore/statement/SQLite/database_sqlite/delete', 1),
        ('Datastore/statement/SQLite/other/other', 6)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/SQLite/all', 11),
        ('Datastore/SQLite/allOther', 11),
        ('Datastore/operation/SQLite/select', 1),
        ('Datastore/statement/SQLite/database_sqlite/select', 1),
        ('Datastore/operation/SQLite/insert', 1),
        ('Datastore/statement/SQLite/database_sqlite/insert', 1),
        ('Datastore/operation/SQLite/update', 1),
        ('Datastore/statement/SQLite/database_sqlite/update', 1),
        ('Datastore/operation/SQLite/delete', 1),
        ('Datastore/statement/SQLite/database_sqlite/delete', 1),
        ('Datastore/instance/SQLite/localhost:{:memory:}/database_sqlite', 4),
        ('Datastore/operation/SQLite/other', 6),
        ('Datastore/statement/SQLite/other/other', 6)]

if is_pypy:
    _test_execute_via_cursor_scoped_metrics.extend([
        ('Function/_sqlite3:Connection.__exit__', 1)])
    _test_execute_via_cursor_rollup_metrics.extend([
        ('Function/_sqlite3:Connection.__exit__', 1)])
else:
    _test_execute_via_cursor_scoped_metrics.extend([
        ('Function/sqlite3:Connection.__exit__', 1)])
    _test_execute_via_cursor_rollup_metrics.extend([
        ('Function/sqlite3:Connection.__exit__', 1)])

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
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
        ('Datastore/statement/SQLite/database_sqlite/select', 1),
        ('Datastore/statement/SQLite/database_sqlite/insert', 1),
        ('Datastore/statement/SQLite/database_sqlite/update', 1),
        ('Datastore/statement/SQLite/database_sqlite/delete', 1),
        ('Datastore/statement/SQLite/other/other', 6)]

_test_execute_via_connection_rollup_metrics = [
        ('Datastore/SQLite/all', 11),
        ('Datastore/SQLite/allOther', 11),
        ('Datastore/operation/SQLite/select', 1),
        ('Datastore/statement/SQLite/database_sqlite/select', 1),
        ('Datastore/operation/SQLite/insert', 1),
        ('Datastore/statement/SQLite/database_sqlite/insert', 1),
        ('Datastore/operation/SQLite/update', 1),
        ('Datastore/statement/SQLite/database_sqlite/update', 1),
        ('Datastore/operation/SQLite/delete', 1),
        ('Datastore/statement/SQLite/database_sqlite/delete', 1),
        ('Datastore/instance/SQLite/localhost:{:memory:}/database_sqlite', 4),
        ('Datastore/operation/SQLite/other', 6),
        ('Datastore/statement/SQLite/other/other', 6)]

if is_pypy:
    _test_execute_via_connection_scoped_metrics.extend([
        ('Function/_sqlite3:Connection.__enter__', 1),
        ('Function/_sqlite3:Connection.__exit__', 1)])
    _test_execute_via_connection_rollup_metrics.extend([
        ('Function/_sqlite3:Connection.__enter__', 1),
        ('Function/_sqlite3:Connection.__exit__', 1)])
else:
    _test_execute_via_connection_scoped_metrics.extend([
        ('Function/sqlite3:Connection.__enter__', 1),
        ('Function/sqlite3:Connection.__exit__', 1)])
    _test_execute_via_connection_rollup_metrics.extend([
        ('Function/sqlite3:Connection.__enter__', 1),
        ('Function/sqlite3:Connection.__exit__', 1)])

@validate_transaction_metrics('test_database:test_execute_via_connection',
        scoped_metrics=_test_execute_via_connection_scoped_metrics,
        rollup_metrics=_test_execute_via_connection_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
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

_test_rollback_on_exception_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Datastore/statement/SQLite/other/other', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/SQLite/all', 2),
        ('Datastore/SQLite/allOther', 2),
        ('Datastore/operation/SQLite/other', 1),
        ('Datastore/statement/SQLite/other/other', 1)]

if is_pypy:
    _test_rollback_on_exception_scoped_metrics.extend([
        ('Function/_sqlite3:Connection.__enter__', 1),
        ('Function/_sqlite3:Connection.__exit__', 1)])
    _test_rollback_on_exception_rollup_metrics.extend([
        ('Function/_sqlite3:Connection.__enter__', 1),
        ('Function/_sqlite3:Connection.__exit__', 1)])
else:
    _test_rollback_on_exception_scoped_metrics.extend([
        ('Function/sqlite3:Connection.__enter__', 1),
        ('Function/sqlite3:Connection.__exit__', 1)])
    _test_rollback_on_exception_rollup_metrics.extend([
        ('Function/sqlite3:Connection.__enter__', 1),
        ('Function/sqlite3:Connection.__exit__', 1)])

@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        with database.connect(DATABASE_NAME) as connection:
            raise RuntimeError('error')
    except RuntimeError:
        pass
