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

import psycopg2cffi
import psycopg2cffi.extensions
import psycopg2cffi.extras
import pytest

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_database_node import (
    validate_database_node,
)
from testing_support.validators.validate_transaction_slow_sql_count import \
        validate_transaction_slow_sql_count
from newrelic.api.background_task import background_task
from newrelic.core.database_utils import SQLConnections

from testing_support.db_settings import postgresql_settings
DB_SETTINGS = postgresql_settings()[0]


def _exercise_db(cursor_kwargs=None):
    cursor_kwargs = cursor_kwargs or {}

    connection = psycopg2cffi.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor(**cursor_kwargs)

        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))
    finally:
        connection.close()


# Tests


def explain_plan_is_not_none(node):
    with SQLConnections() as connections:
        explain_plan = node.explain_plan(connections)

    assert explain_plan is not None


@override_application_settings({
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.record_sql': 'raw',
})
@validate_database_node(explain_plan_is_not_none)
@validate_transaction_slow_sql_count(1)
@background_task(name='test_explain_plan_named_cursors')
@pytest.mark.parametrize('withhold', (True, False))
@pytest.mark.parametrize('scrollable', (True, False))
def test_explain_plan_named_cursors(withhold, scrollable):
    cursor_kwargs = {
        'name': 'test_explain_plan_named_cursors',
    }

    if withhold:
        cursor_kwargs['withhold'] = withhold

    if scrollable:
        cursor_kwargs['scrollable'] = scrollable

    _exercise_db(cursor_kwargs=cursor_kwargs)
