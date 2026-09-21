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

from conftest import OPENSEARCH_SETTINGS
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = [
    ("Datastore/operation/OpenSearch/cat.health", 1),
    ("Datastore/operation/OpenSearch/nodes.info", 1),
    ("Datastore/operation/OpenSearch/snapshot.status", 1),
    ("Datastore/statement/OpenSearch/_all/cluster.health", 1),
    ("Datastore/statement/OpenSearch/_all/search", 2),
    ("Datastore/statement/OpenSearch/address/index", 2),
    ("Datastore/statement/OpenSearch/address/search", 1),
    ("Datastore/statement/OpenSearch/contacts/index", 3),
    ("Datastore/statement/OpenSearch/contacts/indices.refresh", 1),
    ("Datastore/statement/OpenSearch/contacts/search", 2),
    ("Datastore/statement/OpenSearch/other/search", 2),
]

_all_count = 17
_base_rollup_metrics = [
    ("Datastore/all", _all_count),
    ("Datastore/allOther", _all_count),
    ("Datastore/OpenSearch/all", _all_count),
    ("Datastore/OpenSearch/allOther", _all_count),
    ("Datastore/operation/OpenSearch/cat.health", 1),
    ("Datastore/operation/OpenSearch/cluster.health", 1),
    ("Datastore/operation/OpenSearch/index", 5),
    ("Datastore/operation/OpenSearch/indices.refresh", 1),
    ("Datastore/operation/OpenSearch/nodes.info", 1),
    ("Datastore/operation/OpenSearch/search", 7),
    ("Datastore/operation/OpenSearch/snapshot.status", 1),
    ("Datastore/statement/OpenSearch/_all/cluster.health", 1),
    ("Datastore/statement/OpenSearch/_all/search", 2),
    ("Datastore/statement/OpenSearch/address/index", 2),
    ("Datastore/statement/OpenSearch/address/search", 1),
    ("Datastore/statement/OpenSearch/contacts/index", 3),
    ("Datastore/statement/OpenSearch/contacts/indices.refresh", 1),
    ("Datastore/statement/OpenSearch/contacts/search", 2),
    ("Datastore/statement/OpenSearch/other/search", 2),
]

# Instance info

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(OPENSEARCH_SETTINGS["host"])
_port = OPENSEARCH_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/OpenSearch/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, _all_count))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Query


def _exercise_opensearch(client):
    client.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    client.index(index="contacts", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2)
    client.index(index="contacts", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    client.indices.refresh(index="contacts")
    client.index(index="address", body={"name": "Sherlock", "address": "221B Baker Street, London"}, id=1)
    client.index(index="address", body={"name": "Bilbo", "address": "Bag End, Bagshot row, Hobbiton, Shire"}, id=2)
    client.search(index="contacts", q="name:Joe")
    client.search(index="contacts", q="name:jessica")
    client.search(index="address", q="name:Sherlock")
    client.search(index=["contacts", "address"], q="name:Bilbo")
    client.search(index="contacts,address", q="name:Bilbo")
    client.search(index="*", q="name:Bilbo")
    client.search(q="name:Bilbo")
    client.cluster.health()

    if hasattr(client, "cat"):
        client.cat.health()
    if hasattr(client, "nodes"):
        client.nodes.info()
    if hasattr(client, "snapshot") and hasattr(client.snapshot, "status"):
        client.snapshot.status()
    if hasattr(client.indices, "status"):
        client.indices.status()


# Test


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_opensearch:test_opensearch_operation_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_disable_instance_settings)
@background_task()
def test_opensearch_operation_disabled(client):
    _exercise_opensearch(client)


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_opensearch:test_opensearch_operation_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_opensearch_operation_enabled(client):
    _exercise_opensearch(client)


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_opensearch:test_opensearch_operation_enabled_empty_transaction_settings",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_opensearch_operation_enabled_empty_transaction_settings(client):
    transaction = current_transaction()
    settings = transaction._settings
    transaction._settings = None

    _exercise_opensearch(client)

    transaction._settings = settings


def test_opensearch_no_transaction(client):
    _exercise_opensearch(client)
