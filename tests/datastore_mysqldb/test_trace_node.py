import MySQLdb

from testing_support.fixtures import (validate_tt_collector_json,
    override_application_settings)
from testing_support.settings import mysql_multiple_settings
from testing_support.util import instance_hostname

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = mysql_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]


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
    'host': instance_hostname(DB_SETTINGS['host']),
    'port_path_or_id': str(DB_SETTINGS['port']),
    'db.instance': DB_SETTINGS['name'],
}
_enabled_forgone = {}

_disabled_required = {}
_disabled_forgone = {
    'host': 'VALUE NOT USED',
    'port_path_or_id': 'VALUE NOT USED',
    'db.instance': 'VALUE NOT USED',
}


# Query

def _exercise_db():
    connection = MySQLdb.connect(db=DB_SETTINGS['name'],
            user=DB_SETTINGS['user'], passwd=DB_SETTINGS['password'],
            host=DB_SETTINGS['host'], port=DB_SETTINGS['port'])
    with connection as cursor:
        cursor.execute('SELECT version();')
    connection.commit()


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
