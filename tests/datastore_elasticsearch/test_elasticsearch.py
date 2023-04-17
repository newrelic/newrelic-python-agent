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

import elasticsearch.client
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

from conftest import ES_VERSION, ES_SETTINGS


# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
}

# Metrics

_base_scoped_metrics = [
    ("Datastore/statement/Elasticsearch/_all/cluster.health", 1),
    ("Datastore/statement/Elasticsearch/_all/search", 2),
    ("Datastore/statement/Elasticsearch/address/index", 2),
    ("Datastore/statement/Elasticsearch/address/search", 1),
    ("Datastore/statement/Elasticsearch/contacts/index", 3),
    ("Datastore/statement/Elasticsearch/contacts/indices.refresh", 1),
    ("Datastore/statement/Elasticsearch/contacts/search", 2),
    ("Datastore/statement/Elasticsearch/other/search", 2),
]

_base_rollup_metrics = [
    ("Datastore/operation/Elasticsearch/cluster.health", 1),
    ("Datastore/operation/Elasticsearch/index", 5),
    ("Datastore/operation/Elasticsearch/indices.refresh", 1),
    ("Datastore/operation/Elasticsearch/search", 7),
    ("Datastore/statement/Elasticsearch/_all/cluster.health", 1),
    ("Datastore/statement/Elasticsearch/_all/search", 2),
    ("Datastore/statement/Elasticsearch/address/index", 2),
    ("Datastore/statement/Elasticsearch/address/search", 1),
    ("Datastore/statement/Elasticsearch/contacts/index", 3),
    ("Datastore/statement/Elasticsearch/contacts/indices.refresh", 1),
    ("Datastore/statement/Elasticsearch/contacts/search", 2),
    ("Datastore/statement/Elasticsearch/other/search", 2),
]

# Version support

def is_importable(module_path):
    try:
        __import__(module_path)
        return True
    except ImportError:
        return False


_all_count = 14

if is_importable("elasticsearch.client.cat") or is_importable("elasticsearch._sync.client.cat"):
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/cat.health", 1))
    _base_rollup_metrics.append(("Datastore/operation/Elasticsearch/cat.health", 1))
    _all_count += 1
else:
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/cat.health", None))
    _base_rollup_metrics.append(("Datastore/operation/Elasticsearch/cat.health", None))

if is_importable("elasticsearch.client.nodes") or is_importable("elasticsearch._sync.client.nodes"):
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/nodes.info", 1))
    _base_rollup_metrics.append(("Datastore/operation/Elasticsearch/nodes.info", 1))
    _all_count += 1
else:
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/nodes.info", None))
    _base_rollup_metrics.append(("Datastore/operation/Elasticsearch/nodes.info", None))

if hasattr(elasticsearch.client, "SnapshotClient") and hasattr(elasticsearch.client.SnapshotClient, "status"):
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/snapshot.status", 1))
    _base_rollup_metrics.append(("Datastore/operation/Elasticsearch/snapshot.status", 1))
    _all_count += 1
else:
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/snapshot.status", None))
    _base_rollup_metrics.append(("Datastore/operation/Elasticsearch/snapshot.status", None))

if hasattr(elasticsearch.client.IndicesClient, "status"):
    _base_scoped_metrics.append(("Datastore/statement/Elasticsearch/_all/indices.status", 1))
    _base_rollup_metrics.extend(
        [
            ("Datastore/operation/Elasticsearch/indices.status", 1),
            ("Datastore/statement/Elasticsearch/_all/indices.status", 1),
        ]
    )
    _all_count += 1
else:
    _base_scoped_metrics.append(("Datastore/operation/Elasticsearch/indices.status", None))
    _base_rollup_metrics.extend(
        [
            ("Datastore/operation/Elasticsearch/indices.status", None),
            ("Datastore/statement/Elasticsearch/_all/indices.status", None),
        ]
    )

_base_rollup_metrics.extend(
    [
        ("Datastore/all", _all_count),
        ("Datastore/allOther", _all_count),
        ("Datastore/Elasticsearch/all", _all_count),
        ("Datastore/Elasticsearch/allOther", _all_count),
    ]
)

# Instance info

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(ES_SETTINGS["host"])
_port = ES_SETTINGS["port"]

_instance_metric_name = "Datastore/instance/Elasticsearch/%s/%s" % (_host, _port)

_enable_rollup_metrics.append((_instance_metric_name, _all_count))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Query


def _exercise_es_v7(es):
    es.index(index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    es.index(
        index="contacts", doc_type="person", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2
    )
    es.index(index="contacts", doc_type="person", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    es.indices.refresh("contacts")
    es.index(
        index="address", doc_type="employee", body={"name": "Sherlock", "address": "221B Baker Street, London"}, id=1
    )
    es.index(
        index="address",
        doc_type="employee",
        body={"name": "Bilbo", "address": "Bag End, Bagshot row, Hobbiton, Shire"},
        id=2,
    )
    es.search(index="contacts", q="name:Joe")
    es.search(index="contacts", q="name:jessica")
    es.search(index="address", q="name:Sherlock")
    es.search(index=["contacts", "address"], q="name:Bilbo")
    es.search(index="contacts,address", q="name:Bilbo")
    es.search(index="*", q="name:Bilbo")
    es.search(q="name:Bilbo")
    es.cluster.health()

    if hasattr(es, "cat"):
        es.cat.health()
    if hasattr(es, "nodes"):
        es.nodes.info()
    if hasattr(es, "snapshot") and hasattr(es.snapshot, "status"):
        es.snapshot.status()
    if hasattr(es.indices, "status"):
        es.indices.status()


def _exercise_es_v8(es):
    es.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    es.index(index="contacts", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2)
    es.index(index="contacts", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    es.indices.refresh(index="contacts")
    es.index(index="address", body={"name": "Sherlock", "address": "221B Baker Street, London"}, id=1)
    es.index(index="address", body={"name": "Bilbo", "address": "Bag End, Bagshot row, Hobbiton, Shire"}, id=2)
    es.search(index="contacts", q="name:Joe")
    es.search(index="contacts", q="name:jessica")
    es.search(index="address", q="name:Sherlock")
    es.search(index=["contacts", "address"], q="name:Bilbo")
    es.search(index="contacts,address", q="name:Bilbo")
    es.search(index="*", q="name:Bilbo")
    es.search(q="name:Bilbo")
    es.cluster.health()

    if hasattr(es, "cat"):
        es.cat.health()
    if hasattr(es, "nodes"):
        es.nodes.info()
    if hasattr(es, "snapshot") and hasattr(es.snapshot, "status"):
        es.snapshot.status()
    if hasattr(es.indices, "status"):
        es.indices.status()


_exercise_es = _exercise_es_v7 if ES_VERSION < (8, 0, 0) else _exercise_es_v8


# Test

@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_elasticsearch:test_elasticsearch_operation_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_disable_instance_settings)
@background_task()
def test_elasticsearch_operation_disabled(client):
    _exercise_es(client)


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_elasticsearch:test_elasticsearch_operation_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_elasticsearch_operation_enabled(client):
    _exercise_es(client)
