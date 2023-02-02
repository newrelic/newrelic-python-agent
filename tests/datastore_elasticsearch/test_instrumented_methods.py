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

import elasticsearch
import elasticsearch.client
from conftest import ES_VERSION
from testing_support.validators.validate_datastore_trace_inputs import (
    validate_datastore_trace_inputs,
)

from newrelic.api.background_task import background_task
from newrelic.hooks.datastore_elasticsearch import (
    _elasticsearch_client_cat_methods,
    _elasticsearch_client_cluster_methods,
    _elasticsearch_client_indices_methods,
    _elasticsearch_client_ingest_methods,
    _elasticsearch_client_methods,
    _elasticsearch_client_nodes_methods,
    _elasticsearch_client_snapshot_methods,
    _elasticsearch_client_tasks_methods,
)


def client(client):
    if ES_VERSION < (8, 0):
        client.index(
            index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1
        )
    else:
        client.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    return client


@validate_datastore_trace_inputs(target="contacts", operation="exists")
@background_task()
def test_method_on_client_datastore_trace_inputs(client):
    client.exists(index="contacts", id=1)


def _test_methods_wrapped(object, method_name_tuples):
    for method_name, _ in method_name_tuples:
        method = getattr(object, method_name, None)
        if method is not None:
            err = "%s.%s isnt being wrapped" % (object, method)
            assert hasattr(method, "__wrapped__"), err


def test_instrumented_methods_client():
    _test_methods_wrapped(elasticsearch.Elasticsearch, _elasticsearch_client_methods)


def test_instrumented_methods_client_indices():
    _test_methods_wrapped(elasticsearch.client.IndicesClient, _elasticsearch_client_indices_methods)


def test_instrumented_methods_client_cluster():
    _test_methods_wrapped(elasticsearch.client.ClusterClient, _elasticsearch_client_cluster_methods)


def test_instrumented_methods_client_cat():
    if hasattr(elasticsearch.client, "CatClient"):
        _test_methods_wrapped(elasticsearch.client.CatClient, _elasticsearch_client_cat_methods)


def test_instrumented_methods_client_nodes():
    if hasattr(elasticsearch.client, "NodesClient"):
        _test_methods_wrapped(elasticsearch.client.NodesClient, _elasticsearch_client_nodes_methods)


def test_instrumented_methods_client_snapshot():
    if hasattr(elasticsearch.client, "SnapshotClient"):
        _test_methods_wrapped(elasticsearch.client.SnapshotClient, _elasticsearch_client_snapshot_methods)


def test_instrumented_methods_client_tasks():
    if hasattr(elasticsearch.client, "TasksClient"):
        _test_methods_wrapped(elasticsearch.client.TasksClient, _elasticsearch_client_tasks_methods)


def test_instrumented_methods_client_ingest():
    if hasattr(elasticsearch.client, "IngestClient"):
        _test_methods_wrapped(elasticsearch.client.IngestClient, _elasticsearch_client_ingest_methods)
