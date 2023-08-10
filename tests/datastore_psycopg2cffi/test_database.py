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

import psycopg2cffi
import psycopg2cffi.extensions
import psycopg2cffi.extras

from testing_support.fixtures import validate_stats_engine_explain_plan_output_is_none
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_slow_sql_count import \
        validate_transaction_slow_sql_count
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs

from testing_support.db_settings import postgresql_settings

from newrelic.api.background_task import background_task

DB_SETTINGS = postgresql_settings()[0]

_test_execute_via_cursor_scoped_metrics = [
        ('Function/psycopg2cffi:connect', 1),
        ('Function/psycopg2cffi._impl.connection:Connection.__enter__', 1),
        ('Function/psycopg2cffi._impl.connection:Connection.__exit__', 1),
        ('Datastore/statement/Postgres/%s/select' % DB_SETTINGS["table_name"], 1),
        ('Datastore/statement/Postgres/%s/insert' % DB_SETTINGS["table_name"], 1),
        ('Datastore/statement/Postgres/%s/update' % DB_SETTINGS["table_name"], 1),
        ('Datastore/statement/Postgres/%s/delete' % DB_SETTINGS["table_name"], 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/commit', 3),
        ('Datastore/operation/Postgres/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 13),
        ('Datastore/allOther', 13),
        ('Datastore/Postgres/all', 13),
        ('Datastore/Postgres/allOther', 13),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/%s/select' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/%s/insert' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/%s/update' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/%s/delete' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/call', 2),
        ('Datastore/operation/Postgres/commit', 3),
        ('Datastore/operation/Postgres/rollback', 1)]


@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    with psycopg2cffi.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        cursor = connection.cursor()

        psycopg2cffi.extensions.register_type(psycopg2cffi.extensions.UNICODE)
        psycopg2cffi.extensions.register_type(
            psycopg2cffi.extensions.UNICODE,
            connection)
        psycopg2cffi.extensions.register_type(
            psycopg2cffi.extensions.UNICODE,
            cursor)

        cursor.execute("""drop table if exists %s""" % DB_SETTINGS["table_name"])

        cursor.execute("""create table %s """ % DB_SETTINGS["table_name"] +
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into %s """ % DB_SETTINGS["table_name"] +
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from %s""" % DB_SETTINGS["table_name"])

        for row in cursor:
            pass

        cursor.execute("""update %s""" % DB_SETTINGS["table_name"] + """ set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from %s where a=2""" % DB_SETTINGS["table_name"])

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0,))

        connection.rollback()
        connection.commit()


_test_rollback_on_exception_scoped_metrics = [
        ('Function/psycopg2cffi:connect', 1),
        ('Function/psycopg2cffi._impl.connection:Connection.__enter__', 1),
        ('Function/psycopg2cffi._impl.connection:Connection.__exit__', 1),
        ('Datastore/operation/Postgres/rollback', 1)]


_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Postgres/all', 2),
        ('Datastore/Postgres/allOther', 2)]


@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        with psycopg2cffi.connect(
                database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
                password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
                port=DB_SETTINGS['port']):

            raise RuntimeError('error')
    except RuntimeError:
        pass


_test_async_mode_scoped_metrics = [
        ('Function/psycopg2cffi:connect', 1),
        ('Datastore/statement/Postgres/%s/select' % DB_SETTINGS["table_name"], 1),
        ('Datastore/statement/Postgres/%s/insert' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)]

_test_async_mode_rollup_metrics = [
        ('Datastore/all', 5),
        ('Datastore/allOther', 5),
        ('Datastore/Postgres/all', 5),
        ('Datastore/Postgres/allOther', 5),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/%s/select' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/%s/insert' % DB_SETTINGS["table_name"], 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)]


@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics('test_database:test_async_mode',
        scoped_metrics=_test_async_mode_scoped_metrics,
        rollup_metrics=_test_async_mode_rollup_metrics,
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_async_mode():

    wait = psycopg2cffi.extras.wait_select

    kwargs = {}
    version = tuple(int(_) for _ in psycopg2cffi.__version__.split('.'))
    if version >= (2, 8):
        kwargs['async_'] = 1
    else:
        kwargs['async'] = 1

    async_conn = psycopg2cffi.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], **kwargs
    )
    wait(async_conn)
    async_cur = async_conn.cursor()

    async_cur.execute("""drop table if exists %s""" % DB_SETTINGS["table_name"])
    wait(async_cur.connection)

    async_cur.execute("""create table %s """ % DB_SETTINGS["table_name"] + 
            """(a integer, b real, c text)""")
    wait(async_cur.connection)

    async_cur.execute("""insert into %s """ % DB_SETTINGS["table_name"] + 
        """values (%s, %s, %s)""", (1, 1.0, '1.0'))
    wait(async_cur.connection)

    async_cur.execute("""select * from %s""" % DB_SETTINGS["table_name"])
    wait(async_cur.connection)

    for row in async_cur:
        assert isinstance(row, tuple)

    async_conn.close()
