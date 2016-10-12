import psycopg2
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)
from utils import DB_SETTINGS, PSYCOPG2_VERSION

from newrelic.agent import background_task, global_settings


settings = global_settings()

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
@validate_transaction_metrics('test_rollback:test_rollback_on_exception',
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
