import psycopg2
import psycopg2.extensions
import psycopg2.extras

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, override_application_settings)
from utils import instance_hostname, DB_SETTINGS, PSYCOPG2_VERSION

from newrelic.agent import background_task


# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1),
)

_base_rollup_metrics = (
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
        ('Datastore/operation/Postgres/rollback', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

if PSYCOPG2_VERSION > (2, 4):
    _enable_scoped_metrics.append(('Function/psycopg2:connect', 1))
    _disable_scoped_metrics.append(('Function/psycopg2:connect', 1))
else:
    _enable_scoped_metrics.append(('Function/psycopg2._psycopg:connect', 1))
    _disable_scoped_metrics.append(('Function/psycopg2._psycopg:connect', 1))

_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/Postgres/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 11)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

# Query

def _exercise_db(cursor_factory=None, row_type=tuple):
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        if cursor_factory:
            cursor = connection.cursor(cursor_factory=cursor_factory)
        else:
            cursor = connection.cursor()

        unicode_type = psycopg2.extensions.UNICODE
        psycopg2.extensions.register_type(unicode_type)
        psycopg2.extensions.register_type(unicode_type, connection)
        psycopg2.extensions.register_type(unicode_type, cursor)

        cursor.execute("""drop table if exists datastore_psycopg2""")

        cursor.execute("""create table datastore_psycopg2 """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into datastore_psycopg2 """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from datastore_psycopg2""")

        for row in cursor:
            assert isinstance(row, row_type)

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

# Tests

@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_enable_instance():
    _exercise_db(cursor_factory=None, row_type=tuple)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_disable_instance():
    _exercise_db(cursor_factory=None, row_type=tuple)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_dict_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict_enable_instance():
    dict_factory = psycopg2.extras.RealDictCursor
    _exercise_db(cursor_factory=dict_factory, row_type=dict)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_dict_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict_disable_instance():
    dict_factory = psycopg2.extras.RealDictCursor
    _exercise_db(cursor_factory=dict_factory, row_type=dict)
