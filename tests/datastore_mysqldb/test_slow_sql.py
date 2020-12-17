import MySQLdb

from testing_support.fixtures import override_application_settings
from testing_support.db_settings import mysql_settings
from testing_support.validators.validate_slow_sql_collector_json import validate_slow_sql_collector_json

from newrelic.api.background_task import background_task

DB_MULTIPLE_SETTINGS = mysql_settings()
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

_enabled_required = set(['host', 'port_path_or_id', 'database_name'])
_enabled_forgone = set()

_disabled_required = set()
_disabled_forgone = set(['host', 'port_path_or_id', 'database_name'])


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
@validate_slow_sql_collector_json(
        required_params=_enabled_required,
        forgone_params=_enabled_forgone)
@background_task()
def test_slow_sql_json_enable_instance():
    _exercise_db()


@override_application_settings(_disable_instance_settings)
@validate_slow_sql_collector_json(
        required_params=_disabled_required,
        forgone_params=_disabled_forgone)
@background_task()
def test_slow_sql_json_disable_instance():
    _exercise_db()
