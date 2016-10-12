import psycopg2
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs)
from utils import DB_MULTIPLE_SETTINGS, PSYCOPG2_VERSION

from newrelic.agent import background_task


# Metrics

_base_scoped_metrics = []

_base_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allOther', 2),
        ('Datastore/Postgres/all', 2),
        ('Datastore/Postgres/allOther', 2),
]

if PSYCOPG2_VERSION > (2, 4):
    _base_scoped_metrics.append(
            ('Function/psycopg2:connect', 2))
else:
    _base_scoped_metrics.append(
            ('Function/psycopg2._psycopg:connect', 2))


# Tests

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@validate_transaction_metrics(
        'test_multiple_dbs:test_multiple_databases',
        scoped_metrics=_base_scoped_metrics,
        rollup_metrics=_base_rollup_metrics,
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
