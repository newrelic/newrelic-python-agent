import psycopg2
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)
from utils import DB_MULTIPLE_SETTINGS

from newrelic.agent import background_task


_test_multiple_databases_scoped_metrics = [
        ('Function/psycopg2:connect', 2),
        ('Function/psycopg2.extensions:connection.__enter__', 2),
        ('Function/psycopg2.extensions:connection.__exit__', 2),
]

_test_multiple_databases_rollup_metrics = [
        ('Datastore/all', 4),
        ('Datastore/allOther', 4),
        ('Datastore/Postgres/all', 4),
        ('Datastore/Postgres/allOther', 4),
]

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@validate_transaction_metrics('test_multiple_dbs:test_multiple_databases',
        scoped_metrics=_test_multiple_databases_scoped_metrics,
        rollup_metrics=_test_multiple_databases_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_multiple_databases():

    postgresql1 = DB_MULTIPLE_SETTINGS[0]
    postgresql2 = DB_MULTIPLE_SETTINGS[1]

    with psycopg2.connect(
            database=postgresql1['name'], user=postgresql1['user'],
            password=postgresql1['password'], host=postgresql1['host'],
            port=postgresql1['port']):
        pass

    with psycopg2.connect(
            database=postgresql2['name'], user=postgresql2['user'],
            password=postgresql2['password'], host=postgresql2['host'],
            port=postgresql2['port']):
        pass
