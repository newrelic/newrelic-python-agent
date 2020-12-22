# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import psycopg2
import pytest

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_slow_sql_collector_json import validate_slow_sql_collector_json

from utils import DB_SETTINGS

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction


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

_distributed_tracing_always_params = set(['guid', 'traceId', 'priority',
    'sampled'])
_distributed_tracing_payload_received_params = set(['parent.type',
    'parent.app', 'parent.account', 'parent.transportType',
    'parent.transportDuration'])

_transaction_guid = '1234567890'
_distributed_tracing_exact_params = {'guid': _transaction_guid}


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

@pytest.mark.parametrize('instance_enabled', (True, False))
@pytest.mark.parametrize('distributed_tracing_enabled,payload_received', [
        (True, True),
        (True, False),
        (False, False),
])
def test_slow_sql_json(instance_enabled, distributed_tracing_enabled,
        payload_received):

    exact_params = None

    if instance_enabled:
        settings = _enable_instance_settings.copy()
        required_params = set(_enabled_required)
        forgone_params = set(_enabled_forgone)
    else:
        settings = _disable_instance_settings.copy()
        required_params = set(_disabled_required)
        forgone_params = set(_disabled_forgone)

    if distributed_tracing_enabled:
        required_params.update(_distributed_tracing_always_params)
        exact_params = _distributed_tracing_exact_params
        settings['distributed_tracing.enabled'] = True
        if payload_received:
            required_params.update(
                    _distributed_tracing_payload_received_params)
        else:
            forgone_params.update(
                    _distributed_tracing_payload_received_params)
    else:
        forgone_params.update(_distributed_tracing_always_params)
        forgone_params.update(_distributed_tracing_payload_received_params)
        settings['distributed_tracing.enabled'] = False

    @override_application_settings(settings)
    @validate_slow_sql_collector_json(
            required_params=required_params,
            forgone_params=forgone_params,
            exact_params=exact_params)
    @background_task()
    def _test():
        transaction = current_transaction()
        transaction.guid = _transaction_guid

        _exercise_db()

        if payload_received:

            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': transaction.settings.account_id,
                    'tk': transaction.settings.trusted_account_key,
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                    'tx': '8703ff3d88eefe9d',
                }
            }

            transaction.accept_distributed_trace_payload(payload)

    _test()
