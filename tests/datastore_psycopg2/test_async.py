import psycopg2
import psycopg2.extras
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, validate_transaction_errors,
    validate_transaction_slow_sql_count,
    validate_stats_engine_explain_plan_output_is_none,
    override_application_settings)
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
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)
)

_base_rollup_metrics = (
        ('Datastore/all', 5),
        ('Datastore/allOther', 5),
        ('Datastore/Postgres/all', 5),
        ('Datastore/Postgres/allOther', 5),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)
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

_enable_scoped_metrics.append(
        ('Datastore/instance/Postgres/%s/%s' % (_host, _port), 4)
)
_enable_rollup_metrics.append(
        ('Datastore/instance/Postgres/%s/%s' % (_host, _port), 4)
)

# Query

def _exercise_db():
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

# Tests

@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 2),
        reason='Async mode not implemented in this version of psycopg2')
@override_application_settings(_enable_instance_settings)
@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics(
        'test_async:test_async_mode_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_async_mode_enable_instance():
    _exercise_db()


@pytest.mark.skipif(PSYCOPG2_VERSION < (2, 2),
        reason='Async mode not implemented in this version of psycopg2')
@override_application_settings(_disable_instance_settings)
@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics(
        'test_async:test_async_mode_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_async_mode_disable_instance():
    _exercise_db()
