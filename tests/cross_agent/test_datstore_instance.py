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

import json
import os
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.database_trace import (register_database_client,
        enable_datastore_instance_feature)
from newrelic.api.transaction import current_transaction
from newrelic.core.database_node import DatabaseNode
from newrelic.core.stats_engine import StatsEngine

FIXTURE = os.path.join(os.curdir,
        'fixtures', 'datastores', 'datastore_instances.json')

_parameters_list = ['name', 'system_hostname', 'db_hostname',
        'product', 'port', 'unix_socket', 'database_path',
        'expected_instance_metric']

_parameters = ','.join(_parameters_list)


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None if f != 'db_hostname' else 'localhost')
            for f in _parameters_list])


_datastore_tests = [_parametrize_test(t) for t in _load_tests()]


@pytest.mark.parametrize(_parameters, _datastore_tests)
@background_task()
def test_datastore_instance(name, system_hostname, db_hostname,
        product, port, unix_socket, database_path,
        expected_instance_metric, monkeypatch):

    monkeypatch.setattr('newrelic.common.system_info.gethostname',
            lambda: system_hostname)

    class FakeModule():
        pass

    register_database_client(FakeModule, product)
    enable_datastore_instance_feature(FakeModule)

    port_path_or_id = port or database_path or unix_socket

    node = DatabaseNode(dbapi2_module=FakeModule,
            sql='',
            children=[],
            start_time=0,
            end_time=1,
            duration=1,
            exclusive=1,
            stack_trace=None,
            sql_format='obfuscated',
            connect_params=None,
            cursor_params=None,
            sql_parameters=None,
            execute_params=None,
            host=db_hostname,
            port_path_or_id=port_path_or_id,
            database_name=database_path,
            guid=None,
            agent_attributes={},
            user_attributes={},
    )

    empty_stats = StatsEngine()
    transaction = current_transaction()
    unscoped_scope = ''

    # Check 'Datastore/instance' metric to confirm that:
    #   1. metric name is reported correctly
    #   2. metric scope is always unscoped

    for metric in node.time_metrics(empty_stats, transaction, None):
        if metric.name.startswith("Datastore/instance/"):
            assert metric.name == expected_instance_metric, name
            assert metric.scope == unscoped_scope
