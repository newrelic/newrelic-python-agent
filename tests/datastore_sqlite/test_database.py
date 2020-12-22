# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlite3 as database
import os
import sys

is_pypy = hasattr(sys, 'pypy_version_info')

from testing_support.fixtures import validate_transaction_metrics
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs

from newrelic.api.background_task import background_task

DATABASE_DIR = os.environ.get('TOX_ENVDIR', '.')
DATABASE_NAME = ':memory:'

_test_execute_via_cursor_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/select', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/insert', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/update', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/delete', 1),
        ('Datastore/operation/SQLite/drop', 1),
        ('Datastore/operation/SQLite/create', 1),
        ('Datastore/operation/SQLite/commit', 3),
        ('Datastore/operation/SQLite/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 11),
        ('Datastore/allOther', 11),
        ('Datastore/SQLite/all', 11),
        ('Datastore/SQLite/allOther', 11),
        ('Datastore/operation/SQLite/select', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/select', 1),
        ('Datastore/operation/SQLite/insert', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/insert', 1),
        ('Datastore/operation/SQLite/update', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/update', 1),
        ('Datastore/operation/SQLite/delete', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/delete', 1),
        ('Datastore/operation/SQLite/drop', 1),
        ('Datastore/operation/SQLite/create', 1),
        ('Datastore/operation/SQLite/commit', 3),
        ('Datastore/operation/SQLite/rollback', 1)]

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

        cursor.execute("""drop table if exists datastore_sqlite""")

        cursor.execute("""create table datastore_sqlite (a, b, c)""")

        cursor.executemany("""insert into datastore_sqlite values (?, ?, ?)""",
                [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_sqlite""")

        for row in cursor: pass

        cursor.execute("""update datastore_sqlite set a=?, b=?, """
                """c=? where a=?""", (4, 4.0, '4.0', 1))

        script = """delete from datastore_sqlite where a = 2;"""
        cursor.executescript(script)

        connection.commit()
        connection.rollback()
        connection.commit()

_test_execute_via_connection_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/select', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/insert', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/update', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/delete', 1),
        ('Datastore/operation/SQLite/drop', 1),
        ('Datastore/operation/SQLite/create', 1),
        ('Datastore/operation/SQLite/commit', 3),
        ('Datastore/operation/SQLite/rollback', 1)]

_test_execute_via_connection_rollup_metrics = [
        ('Datastore/all', 11),
        ('Datastore/allOther', 11),
        ('Datastore/SQLite/all', 11),
        ('Datastore/SQLite/allOther', 11),
        ('Datastore/operation/SQLite/select', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/select', 1),
        ('Datastore/operation/SQLite/insert', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/insert', 1),
        ('Datastore/operation/SQLite/update', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/update', 1),
        ('Datastore/operation/SQLite/delete', 1),
        ('Datastore/statement/SQLite/datastore_sqlite/delete', 1),
        ('Datastore/operation/SQLite/drop', 1),
        ('Datastore/operation/SQLite/create', 1),
        ('Datastore/operation/SQLite/commit', 3),
        ('Datastore/operation/SQLite/rollback', 1)]

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
        connection.execute("""drop table if exists datastore_sqlite""")

        connection.execute("""create table datastore_sqlite (a, b, c)""")

        connection.executemany("""insert into datastore_sqlite values """
                """(?, ?, ?)""", [(1, 1.0, '1.0'), (2, 2.2, '2.2'),
                (3, 3.3, '3.3')])

        connection.execute("""select * from datastore_sqlite""")

        connection.execute("""update datastore_sqlite set a=?, b=?, """
                """c=? where a=?""", (4, 4.0, '4.0', 1))

        script = """delete from datastore_sqlite where a = 2;"""
        connection.executescript(script)

        connection.commit()
        connection.rollback()
        connection.commit()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/_sqlite3:connect', 1),
        ('Datastore/operation/SQLite/rollback', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/SQLite/all', 2),
        ('Datastore/SQLite/allOther', 2),
        ('Datastore/operation/SQLite/rollback', 1)]

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
