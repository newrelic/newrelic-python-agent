import psycopg2

from testing_support.fixtures import validate_slow_sql_collector_json
from utils import DB_SETTINGS

from newrelic.agent import background_task, global_settings


settings = global_settings()

slow_sql_json_required = set()
slow_sql_json_forgone = set()
if 'datastore.instances.r1' in settings.feature_flag:
    # instance/database_name should be reported
    slow_sql_json_required.add('host')
    slow_sql_json_required.add('port_path_or_id')
    slow_sql_json_required.add('database_name')
else:
    # instance/database_name should not be reported
    slow_sql_json_forgone.add('host')
    slow_sql_json_forgone.add('port_path_or_id')
    slow_sql_json_forgone.add('database_name')

@validate_slow_sql_collector_json(required_params=slow_sql_json_required,
        forgone_params=slow_sql_json_forgone)
@background_task()
def test_slow_sql_json():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:
        cursor = connection.cursor()
        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))
