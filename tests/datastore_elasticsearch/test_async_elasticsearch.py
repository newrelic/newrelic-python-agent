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
from conftest import ES_SETTINGS, IS_V8_OR_ABOVE, RUN_IF_V8_OR_ABOVE
from elasticsearch._async import client
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = [
    ("Datastore/operation/Elasticsearch/cat.health", 1),
    ("Datastore/operation/Elasticsearch/nodes.info", 1),
    ("Datastore/operation/Elasticsearch/snapshot.status", 1),
    ("Datastore/statement/Elasticsearch/_all/cluster.health", 1),
    ("Datastore/statement/Elasticsearch/_all/search", 2),
    ("Datastore/statement/Elasticsearch/address/index", 2),
    ("Datastore/statement/Elasticsearch/address/search", 1),
    ("Datastore/statement/Elasticsearch/contacts/index", 3),
    ("Datastore/statement/Elasticsearch/contacts/indices.refresh", 1),
    ("Datastore/statement/Elasticsearch/contacts/search", 2),
    ("Datastore/statement/Elasticsearch/other/search", 2),
]

_all_count = 17
_base_rollup_metrics = [
    ("Datastore/all", _all_count),
    ("Datastore/allOther", _all_count),
    ("Datastore/Elasticsearch/all", _all_count),
    ("Datastore/Elasticsearch/allOther", _all_count),
    ("Datastore/operation/Elasticsearch/cat.health", 1),
    ("Datastore/operation/Elasticsearch/cluster.health", 1),
    ("Datastore/operation/Elasticsearch/index", 5),
    ("Datastore/operation/Elasticsearch/indices.refresh", 1),
    ("Datastore/operation/Elasticsearch/nodes.info", 1),
    ("Datastore/operation/Elasticsearch/search", 7),
    ("Datastore/operation/Elasticsearch/snapshot.status", 1),
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


# Instance info

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_host = instance_hostname(ES_SETTINGS["host"])
_port = ES_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Elasticsearch/{_host}/{_port}"

_enable_rollup_metrics.append((_instance_metric_name, _all_count))

_disable_rollup_metrics.append((_instance_metric_name, None))

# Query


async def _exercise_es_v7(es):
    await es.index(
        index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1
    )
    await es.index(
        index="contacts", doc_type="person", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2
    )
    await es.index(
        index="contacts", doc_type="person", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3
    )
    await es.indices.refresh("contacts")
    await es.index(
        index="address", doc_type="employee", body={"name": "Sherlock", "address": "221B Baker Street, London"}, id=1
    )
    await es.index(
        index="address",
        doc_type="employee",
        body={"name": "Bilbo", "address": "Bag End, Bagshot row, Hobbiton, Shire"},
        id=2,
    )
    await es.search(index="contacts", q="name:Joe")
    await es.search(index="contacts", q="name:jessica")
    await es.search(index="address", q="name:Sherlock")
    await es.search(index=["contacts", "address"], q="name:Bilbo")
    await es.search(index="contacts,address", q="name:Bilbo")
    await es.search(index="*", q="name:Bilbo")
    await es.search(q="name:Bilbo")
    await es.cluster.health()

    if hasattr(es, "cat"):
        await es.cat.health()
    if hasattr(es, "nodes"):
        await es.nodes.info()
    if hasattr(es, "snapshot") and hasattr(es.snapshot, "status"):
        await es.snapshot.status()
    if hasattr(es.indices, "status"):
        await es.indices.status()


async def _exercise_es_v8(es):
    await es.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    await es.index(index="contacts", body={"name": "Jessica Coder", "age": 32, "title": "Programmer"}, id=2)
    await es.index(index="contacts", body={"name": "Freddy Tester", "age": 29, "title": "Assistant"}, id=3)
    await es.indices.refresh(index="contacts")
    await es.index(index="address", body={"name": "Sherlock", "address": "221B Baker Street, London"}, id=1)
    await es.index(index="address", body={"name": "Bilbo", "address": "Bag End, Bagshot row, Hobbiton, Shire"}, id=2)
    await es.search(index="contacts", q="name:Joe")
    await es.search(index="contacts", q="name:jessica")
    await es.search(index="address", q="name:Sherlock")
    await es.search(index=["contacts", "address"], q="name:Bilbo")
    await es.search(index="contacts,address", q="name:Bilbo")
    await es.search(index="*", q="name:Bilbo")
    await es.search(q="name:Bilbo")
    await es.cluster.health()

    if hasattr(es, "cat"):
        await es.cat.health()
    if hasattr(es, "nodes"):
        await es.nodes.info()
    if hasattr(es, "snapshot") and hasattr(es.snapshot, "status"):
        await es.snapshot.status()
    if hasattr(es.indices, "status"):
        await es.indices.status()


_exercise_es = _exercise_es_v8 if IS_V8_OR_ABOVE else _exercise_es_v7


# Test


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_async_elasticsearch:test_async_elasticsearch_operation_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_disable_instance_settings)
@background_task()
def test_async_elasticsearch_operation_disabled(async_client, loop):
    loop.run_until_complete(_exercise_es(async_client))


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_async_elasticsearch:test_async_elasticsearch_operation_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_async_elasticsearch_operation_enabled(async_client, loop):
    loop.run_until_complete(_exercise_es(async_client))


def test_async_elasticsearch_no_transaction(async_client, loop):
    loop.run_until_complete(_exercise_es(async_client))


@RUN_IF_V8_OR_ABOVE
@background_task()
def test_async_elasticsearch_options_no_crash(async_client, loop):
    """Test that the options method on the async client doesn't cause a crash when run with the agent"""

    async def _test():
        client_with_auth = async_client.options(basic_auth=("username", "password"))
        assert client_with_auth is not None
        assert client_with_auth != async_client

        # If options was instrumented, this would cause a crash since the first call would return an unexpected coroutine
        client_chained = async_client.options(basic_auth=("user", "pass")).options(request_timeout=60)
        assert client_chained is not None

    loop.run_until_complete(_test())
