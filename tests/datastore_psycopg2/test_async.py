import psycopg2
import psycopg2.extras

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, validate_transaction_errors,
    validate_transaction_slow_sql_count,
    validate_stats_engine_explain_plan_output_is_none)
from utils import DB_SETTINGS

from newrelic.agent import background_task, global_settings


settings = global_settings()

_test_async_mode_scoped_metrics = [
        ('Function/psycopg2:connect', 1),
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

@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics('test_async:test_async_mode',
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
