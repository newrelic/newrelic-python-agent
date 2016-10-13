import psycopg2

from testing_support.fixtures import (validate_tt_collector_json,
    override_application_settings)
from utils import DB_SETTINGS

from newrelic.agent import background_task


# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
    'datastore_tracer.database_name_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
    'datastore_tracer.database_name_reporting.enabled': False,
}

# Expected parameters

_enabled_required = {
    'host': DB_SETTINGS['host'],
    'port_path_or_id': str(DB_SETTINGS['port']),
    'database_name': DB_SETTINGS['name'],
}
_enabled_forgone = {}

_disabled_required = {}
_disabled_forgone = {
    'host': DB_SETTINGS['host'],
    'port_path_or_id': str(DB_SETTINGS['port']),
    'database_name': DB_SETTINGS['name'],
}

# Query

def _exercise_db():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))
    finally:
        connection.close()

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
