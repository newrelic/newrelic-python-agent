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

@pytest.mark.parametrize('db_instance_enabled', (True, False))
@pytest.mark.parametrize('instance_enabled', (True, False))
def test_span_events(instance_enabled, db_instance_enabled):
    guid = 'dbb533c53b749e0b'
    priority = 0.5

    common_intrinsics = {
        'type': 'Span',
        'transactionId': guid,
        'priority': priority,
        'sampled': True,
        'category': 'datastore',
        'component': 'Postgres',
        'span.kind': 'client',
    }

    exact_agents = {}

    if instance_enabled:
        settings = _enable_instance_settings.copy()
        hostname = instance_hostname(DB_SETTINGS['host'])
        exact_agents.update({
            'peer.address': '%s:%s' % (hostname, DB_SETTINGS['port']),
            'peer.hostname': hostname,
        })
    else:
        settings = _disable_instance_settings.copy()
        exact_agents.update({
            'peer.address': 'Unknown:Unknown',
            'peer.hostname': 'Unknown',
        })

    if db_instance_enabled and instance_enabled:
        exact_agents.update({
            'db.instance': DB_SETTINGS['name'],
        })
        unexpected_agents = ()
    else:
        settings['attributes.exclude'] = ['db.instance']
        unexpected_agents = ('db.instance',)

    query_1_intrinsics = common_intrinsics.copy()
    query_1_intrinsics['name'] = \
            'Datastore/statement/Postgres/pg_settings/select'

    query_1_agents = exact_agents.copy()
    query_1_agents['db.statement'] = \
            'SELECT setting from pg_settings where name=%s'

    query_2_intrinsics = common_intrinsics.copy()
    query_2_intrinsics['name'] = 'Datastore/operation/Postgres/select'

    query_2_agents = exact_agents.copy()
    query_2_agents['db.statement'] = 'SELECT ?'

    @validate_span_events(
            count=1,
            exact_intrinsics=query_1_intrinsics,
            unexpected_intrinsics=('db.instance', 'db.statement'),
            exact_agents=query_1_agents,
            unexpected_agents=unexpected_agents)
    @validate_span_events(
            count=1,
            exact_intrinsics=query_2_intrinsics,
            unexpected_intrinsics=('db.instance', 'db.statement'),
            exact_agents=query_2_agents,
            unexpected_agents=unexpected_agents)
    @override_application_settings(settings)
    @background_task(name='span_events')
    def _test():
        txn = current_transaction()
        txn.guid = guid
        txn._priority = priority
        txn._sampled = True
        _exercise_db()

    _test()
