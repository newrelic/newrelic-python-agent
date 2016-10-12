import psycopg2

from testing_support.fixtures import validate_tt_collector_json
from utils import DB_SETTINGS

from newrelic.agent import background_task, global_settings


settings = global_settings()

if 'datastore.instances.r1' in settings.feature_flag:
    _test_trace_node_datastore_params = {
        'host': DB_SETTINGS['host'],
        'port_path_or_id': str(DB_SETTINGS['port']),
        'database_name': DB_SETTINGS['name'],
    }
    _test_trace_node_datastore_forgone_params = {}
else:
    _test_trace_node_datastore_params = {}
    _test_trace_node_datastore_forgone_params = {
        'host': DB_SETTINGS['host'],
        'port_path_or_id': str(DB_SETTINGS['port']),
        'database_name': DB_SETTINGS['name'],
    }

@validate_tt_collector_json(datastore_params=_test_trace_node_datastore_params,
        datastore_forgone_params=_test_trace_node_datastore_forgone_params)
@background_task()
def test_trace_node_datastore_params():
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
