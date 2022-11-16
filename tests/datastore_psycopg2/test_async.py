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
import psycopg2.extras
import pytest

from testing_support.fixtures import (
    validate_stats_engine_explain_plan_output_is_none,
    override_application_settings)
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_database_trace_inputs import validate_database_trace_inputs
from testing_support.validators.validate_transaction_slow_sql_count import (
    validate_transaction_slow_sql_count)
from testing_support.util import instance_hostname
from testing_support.db_settings import postgresql_settings

DB_SETTINGS = postgresql_settings()[0]

from newrelic.api.background_task import background_task


# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = (
        ('Datastore/statement/Postgres/%s/select' % DB_SETTINGS['table_name'], 1),
        ('Datastore/statement/Postgres/%s/insert' % DB_SETTINGS['table_name'], 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)
)

_base_rollup_metrics = (
        ('Datastore/all', 5),
        ('Datastore/allOther', 5),
        ('Datastore/Postgres/all', 5),
        ('Datastore/Postgres/allOther', 5),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/%s/select' % DB_SETTINGS['table_name'], 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/%s/insert' % DB_SETTINGS['table_name'], 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1)
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics.append(('Function/psycopg2:connect', 1))
_disable_scoped_metrics.append(('Function/psycopg2:connect', 1))

_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/Postgres/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 4)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)

async_keyword_list = ['async', 'async_']


def _exercise_db(async_keyword):
    wait = psycopg2.extras.wait_select

    kwasync = {}
    kwasync[async_keyword] = 1

    async_conn = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'], **kwasync
    )
    wait(async_conn)
    async_cur = async_conn.cursor()

    async_cur.execute("""drop table if exists %s""" % DB_SETTINGS['table_name'])
    wait(async_cur.connection)

    async_cur.execute("""create table %s """ % DB_SETTINGS['table_name'] +
            """(a integer, b real, c text)""")
    wait(async_cur.connection)

    async_cur.execute("""insert into %s """ % DB_SETTINGS['table_name'] +
        """values (%s, %s, %s)""", (1, 1.0, '1.0'))
    wait(async_cur.connection)

    async_cur.execute("""select * from %s""" % DB_SETTINGS['table_name'])
    wait(async_cur.connection)

    for row in async_cur:
        assert isinstance(row, tuple)

    async_conn.close()


# Tests

@override_application_settings(_enable_instance_settings)
@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics(
        'test_async:test_async_mode_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
@pytest.mark.parametrize('async_keyword', async_keyword_list)
def test_async_mode_enable_instance(async_keyword):
    _exercise_db(async_keyword)


@override_application_settings(_disable_instance_settings)
@validate_stats_engine_explain_plan_output_is_none()
@validate_transaction_slow_sql_count(num_slow_sql=4)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@validate_transaction_metrics(
        'test_async:test_async_mode_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
@pytest.mark.parametrize('async_keyword', async_keyword_list)
def test_async_mode_disable_instance(async_keyword):
    _exercise_db(async_keyword)
