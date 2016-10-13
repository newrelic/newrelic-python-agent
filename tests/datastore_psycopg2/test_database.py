import json
import re

import psycopg2
import psycopg2.extensions
import psycopg2.extras
import pytest
import decimal

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, validate_transaction_errors,
    validate_transaction_slow_sql_count,
    validate_stats_engine_explain_plan_output_is_none,
    validate_slow_sql_collector_json,
    validate_tt_collector_json)

from testing_support.settings import postgresql_multiple_settings

from newrelic.agent import background_task, global_settings

DB_MULTIPLE_SETTINGS = postgresql_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]
settings = global_settings()

def _to_int(version_str):
    m = re.match(r'\d+', version_str)
    return int(m.group(0)) if m else 0

def version2tuple(version_str, parts_count=2):
    """Convert version, even if it contains non-numeric chars.

    >>> version2tuple('9.4rc1.1')
    (9, 4)

    """

    parts = version_str.split('.')[:parts_count]
    return tuple(map(_to_int, parts))

def postgresql_version():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))

        return cursor.fetchone()
    finally:
        connection.close()

POSTGRESQL_VERSION = version2tuple(postgresql_version()[0])
PSYCOPG2_VERSION = version2tuple(psycopg2.__version__, parts_count=3)

_test_execute_via_cursor_scoped_metrics = [
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

_test_execute_via_cursor_rollup_metrics = [
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/Postgres/all', 12),
        ('Datastore/Postgres/allOther', 12),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/call', 2),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

# The feature flags are expected to be bound and set
# through env vars at the time the test is imported
if 'datastore.instances.r1' in settings.feature_flag:
    _test_execute_via_cursor_scoped_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 11))
    _test_execute_via_cursor_rollup_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 11))

if PSYCOPG2_VERSION > (2, 4):
    _test_execute_via_cursor_scoped_metrics.append(
            ('Function/psycopg2:connect', 1))
else:
    _test_execute_via_cursor_scoped_metrics.append(
            ('Function/psycopg2._psycopg:connect', 1))

@validate_transaction_metrics('test_database:test_execute_via_cursor',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cursor)

        cursor.execute("""drop table if exists datastore_psycopg2""")

        cursor.execute("""create table datastore_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_psycopg2""")

        for row in cursor:
            assert isinstance(row, tuple)

        cursor.execute("""update datastore_psycopg2 set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_psycopg2 where a=2""")

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()
    finally:
        connection.close()

@validate_transaction_metrics('test_database:test_execute_via_cursor_dict',
        scoped_metrics=_test_execute_via_cursor_scoped_metrics,
        rollup_metrics=_test_execute_via_cursor_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cursor)

        cursor.execute("""drop table if exists datastore_psycopg2""")

        cursor.execute("""create table datastore_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_psycopg2""")

        for row in cursor:
            assert isinstance(row, dict)

        cursor.execute("""update datastore_psycopg2 set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from datastore_psycopg2 where a=2""")

        connection.commit()

        cursor.callproc('now')
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()
    finally:
        connection.close()

_test_rollback_on_exception_scoped_metrics = [
        ('Function/psycopg2:connect', 1),
        ('Datastore/operation/Postgres/rollback', 1)]

_test_rollback_on_exception_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Postgres/all', 2),
        ('Datastore/Postgres/allOther', 2),
        ('Datastore/operation/Postgres/rollback', 1)]

# The feature flags are expected to be bound and set
# through env vars at the time the test is imported
if 'datastore.instances.r1' in settings.feature_flag:
    _test_rollback_on_exception_scoped_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 1))
    _test_rollback_on_exception_rollup_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 1))

@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 5),
        reason='Context manager support introduced in psycopg2 version 2.5')
@validate_transaction_metrics('test_database:test_rollback_on_exception',
        scoped_metrics=_test_rollback_on_exception_scoped_metrics,
        rollup_metrics=_test_rollback_on_exception_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_rollback_on_exception():
    try:
        with psycopg2.connect(
                database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
                password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
                port=DB_SETTINGS['port']):

            raise RuntimeError('error')
    except RuntimeError:
        pass

_test_async_mode_scoped_metrics = [
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)]

_test_async_mode_rollup_metrics = [
        ('Datastore/all', 5),
        ('Datastore/allOther', 5),
        ('Datastore/Postgres/all', 5),
        ('Datastore/Postgres/allOther', 5),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)]

# The feature flags are expected to be bound and set
# through env vars at the time the test is imported
if 'datastore.instances.r1' in settings.feature_flag:
    _test_async_mode_scoped_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' %
            (DB_SETTINGS['host'], DB_SETTINGS['port']), 4))
    _test_async_mode_rollup_metrics.append(
            ('Datastore/instance/Postgres/%s/%s' % (
            DB_SETTINGS['host'], DB_SETTINGS['port']), 4))

if PSYCOPG2_VERSION > (2, 4):
    _test_async_mode_scoped_metrics.append(
            ('Function/psycopg2:connect', 1))
else:
    _test_async_mode_scoped_metrics.append(
            ('Function/psycopg2._psycopg:connect', 1))

@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 2),
        reason='Async mode not implemented in this version of psycopg2')
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

    wait = psycopg2.extras.wait_select

    async_conn = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], async=1
    )
    wait(async_conn)
    async_cur = async_conn.cursor()

    async_cur.execute("""drop table if exists datastore_psycopg2""")
    wait(async_cur.connection)

    async_cur.execute("""create table datastore_psycopg2 """
            """(a integer, b real, c text)""")
    wait(async_cur.connection)

    async_cur.execute("""insert into datastore_psycopg2 """
        """values (%s, %s, %s)""", (1, 1.0, '1.0'))
    wait(async_cur.connection)

    async_cur.execute("""select * from datastore_psycopg2""")
    wait(async_cur.connection)

    for row in async_cur:
        assert isinstance(row, tuple)

    async_conn.close()

@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 5),
        reason='Register json not implemented in this version of psycopg2')
@pytest.mark.skipif(POSTGRESQL_VERSION < (9, 2),
        reason="JSON data type was introduced in Postgres 9.2")
@validate_transaction_metrics('test_database:test_register_json',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_json():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])
    try:
        cursor = connection.cursor()

        loads = lambda x: json.loads(x, parse_float=decimal.Decimal)
        psycopg2.extras.register_json(connection, loads=loads)
        psycopg2.extras.register_json(cursor, loads=loads)
    finally:
        connection.close()

@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 5),
        reason='Register range not implemented in this version of psycopg2')
@pytest.mark.skipif(POSTGRESQL_VERSION < (9, 2),
        reason="Range types were introduced in Postgres 9.2")
@validate_transaction_metrics('test_database:test_register_range',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_range():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])
    try:
        create_sql = ('CREATE TYPE floatrange AS RANGE ('
                      'subtype = float8,'
                      'subtype_diff = float8mi)')

        cursor = connection.cursor()

        cursor.execute("DROP TYPE if exists floatrange")
        cursor.execute(create_sql)

        psycopg2.extras.register_range('floatrange',
                psycopg2.extras.NumericRange, connection)

        cursor.execute("DROP TYPE if exists floatrange")
        cursor.execute(create_sql)

        psycopg2.extras.register_range('floatrange',
                psycopg2.extras.NumericRange, cursor)

        cursor.execute("DROP TYPE if exists floatrange")
    finally:
        connection.close()

_test_multiple_databases_scoped_metrics = []

_test_multiple_databases_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Postgres/all', 2),
        ('Datastore/Postgres/allOther', 2),
]

if PSYCOPG2_VERSION > (2, 4):
    _test_multiple_databases_scoped_metrics.append(
            ('Function/psycopg2:connect', 2))
else:
    _test_multiple_databases_scoped_metrics.append(
            ('Function/psycopg2._psycopg:connect', 2))

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@validate_transaction_metrics('test_database:test_multiple_databases',
        scoped_metrics=_test_multiple_databases_scoped_metrics,
        rollup_metrics=_test_multiple_databases_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_multiple_databases():

    postgresql1 = DB_MULTIPLE_SETTINGS[0]
    postgresql2 = DB_MULTIPLE_SETTINGS[1]

    connection = psycopg2.connect(
            database=postgresql1['name'], user=postgresql1['user'],
            password=postgresql1['password'], host=postgresql1['host'],
            port=postgresql1['port'])
    connection.close()

    connection = psycopg2.connect(
            database=postgresql2['name'], user=postgresql2['user'],
            password=postgresql2['password'], host=postgresql2['host'],
            port=postgresql2['port'])
    connection.close()
