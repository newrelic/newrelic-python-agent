import pytest
import psycopg2

from newrelic.api.transaction import current_transaction
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)
from testing_support.util import instance_hostname
from utils import DB_SETTINGS

from newrelic.api.background_task import background_task


# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
    'datastore_tracer.database_name_reporting.enabled': True,
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
    'datastore_tracer.database_name_reporting.enabled': False,
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
}

# Expected parameters

_enabled_required = {
    'datastoreHost': instance_hostname(DB_SETTINGS['host']),
    'datastorePortPathOrId': str(DB_SETTINGS['port']),
    'datastoreName': DB_SETTINGS['name'],
}
_enabled_forgone = []

_disabled_required = {}
_disabled_forgone = [
    'datastoreHost',
    'datastorePortPathOrId',
    'datastoreName',
]


def _exercise_db():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))

        # No target
        cursor.execute('SELECT 1')
    finally:
        connection.close()


# Tests

@pytest.mark.parametrize('instance_enabled', (True, False))
def test_span_events(instance_enabled):
    guid = 'dbb533c53b749e0b'
    priority = 0.5

    common = {
        'type': 'Span',
        'appLocalRootId': guid,
        'priority': priority,
        'sampled': True,
        'category': 'datastore',
        'datastoreProduct': 'Postgres',
        'datastoreOperation': 'select',
    }

    if instance_enabled:
        settings = _enable_instance_settings
        forgone = _enabled_forgone
        common.update(_enabled_required)
    else:
        forgone = _disabled_forgone
        settings = _disable_instance_settings
        common.update(_disabled_required)

    query_1 = common.copy()
    query_1['datastoreCollection'] = 'pg_settings'
    query_1['name'] = 'Datastore/statement/Postgres/pg_settings/select'

    query_2 = common.copy()
    query_2['name'] = 'Datastore/operation/Postgres/select'

    @validate_span_events(count=1, exact_intrinsics=query_1)
    @validate_span_events(count=1, exact_intrinsics=query_2)
    @override_application_settings(settings)
    @background_task(name='span_events')
    def _test():
        txn = current_transaction()
        txn.guid = guid
        txn._priority = priority
        txn._sampled = True
        _exercise_db()

    for attr in forgone:
        _test = validate_span_events(
                count=0, expected_intrinsics=(attr,))(_test)

    _test()
