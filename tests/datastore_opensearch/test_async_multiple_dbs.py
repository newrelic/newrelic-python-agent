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
from conftest import OPENSEARCH_MULTIPLE_SETTINGS
from opensearchpy import AsyncOpenSearch
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = (("Datastore/statement/OpenSearch/contacts/index", 2),)

_base_rollup_metrics = (
    ("Datastore/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/OpenSearch/all", 2),
    ("Datastore/OpenSearch/allOther", 2),
    ("Datastore/operation/OpenSearch/index", 2),
    ("Datastore/statement/OpenSearch/contacts/index", 2),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

if len(OPENSEARCH_MULTIPLE_SETTINGS) > 1:
    opensearch_1 = OPENSEARCH_MULTIPLE_SETTINGS[0]
    opensearch_2 = OPENSEARCH_MULTIPLE_SETTINGS[1]

    host_1 = instance_hostname(opensearch_1["host"])
    port_1 = opensearch_1["port"]

    host_2 = instance_hostname(opensearch_2["host"])
    port_2 = opensearch_2["port"]

    instance_metric_name_1 = f"Datastore/instance/OpenSearch/{host_1}/{port_1}"
    instance_metric_name_2 = f"Datastore/instance/OpenSearch/{host_2}/{port_2}"

    _enable_rollup_metrics.extend([(instance_metric_name_1, 1), (instance_metric_name_2, 1)])

    _disable_rollup_metrics.extend([(instance_metric_name_1, None), (instance_metric_name_2, None)])

# Query


async def _exercise_opensearch(client):
    await client.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)


# Test


@pytest.fixture(scope="session")
def clients(loop):
    clients = []
    for db in OPENSEARCH_MULTIPLE_SETTINGS:
        opensearch_url = f"http://{db['host']}:{db['port']}"
        clients.append(AsyncOpenSearch(opensearch_url))

    yield clients

    for client in clients:
        loop.run_until_complete(client.close())


@pytest.mark.skipif(
    len(OPENSEARCH_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases."
)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_async_multiple_dbs:test_multiple_dbs_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_dbs_enabled(clients, loop):
    import asyncio

    # Run multiple queries in parallel
    loop.run_until_complete(asyncio.gather(*(_exercise_opensearch(client) for client in clients)))


@pytest.mark.skipif(
    len(OPENSEARCH_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases."
)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_async_multiple_dbs:test_multiple_dbs_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_dbs_disabled(clients, loop):
    import asyncio

    # Run multiple queries in parallel
    loop.run_until_complete(asyncio.gather(*(_exercise_opensearch(client) for client in clients)))
