import redis

from testing_support.fixtures import (validate_tt_collector_json,
    override_application_settings)
from testing_support.util import instance_hostname
from testing_support.settings import redis_multiple_settings

from newrelic.agent import background_task

DB_MULTIPLE_SETTINGS = redis_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]
DATABASE_NUMBER = 0

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
    'datastore_tracer.database_name_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
    'datastore_tracer.database_name_reporting.enabled': False,
}
_instance_only_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
    'datastore_tracer.database_name_reporting.enabled': False,
}
_database_only_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
    'datastore_tracer.database_name_reporting.enabled': True,
}

# Expected parameters

_enabled_required = {
    'host': instance_hostname(DB_SETTINGS['host']),
    'port_path_or_id': str(DB_SETTINGS['port']),
    'database_name': str(DATABASE_NUMBER),
}
_enabled_forgone = {}

_disabled_required = {}
_disabled_forgone = {
    'host': 'VALUE NOT USED',
    'port_path_or_id': 'VALUE NOT USED',
    'database_name': 'VALUE NOT USED',
}

_instance_only_required = {
    'host': instance_hostname(DB_SETTINGS['host']),
    'port_path_or_id': str(DB_SETTINGS['port']),
}
_instance_only_forgone = {
    'database_name': str(DATABASE_NUMBER),
}

_database_only_required = {
    'database_name': str(DATABASE_NUMBER),
}
_database_only_forgone = {
    'host': 'VALUE NOT USED',
    'port_path_or_id': 'VALUE NOT USED',
}

# Query

def _exercise_db():
    client = redis.StrictRedis(host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], db=DATABASE_NUMBER)

    client.set('key', 'value')
    client.get('key')

    client.execute_command('CLIENT', 'LIST', parse='LIST')

# Tests

@override_application_settings(_enable_instance_settings)
@validate_tt_collector_json(
        datastore_params=_enabled_required,
        datastore_forgone_params=_enabled_forgone)
@background_task()
def test_trace_node_datastore_params_enable_instance():
    _exercise_db()


@override_application_settings(_disable_instance_settings)
@validate_tt_collector_json(
        datastore_params=_disabled_required,
        datastore_forgone_params=_disabled_forgone)
@background_task()
def test_trace_node_datastore_params_disable_instance():
    _exercise_db()

@override_application_settings(_instance_only_settings)
@validate_tt_collector_json(
        datastore_params=_instance_only_required,
        datastore_forgone_params=_instance_only_forgone)
@background_task()
def test_trace_node_datastore_params_instance_only():
    _exercise_db()

@override_application_settings(_database_only_settings)
@validate_tt_collector_json(
        datastore_params=_database_only_required,
        datastore_forgone_params=_database_only_forgone)
@background_task()
def test_trace_node_datastore_params_database_only():
    _exercise_db()
