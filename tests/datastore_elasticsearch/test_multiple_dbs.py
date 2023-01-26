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
from conftest import ES_MULTIPLE_SETTINGS, ES_VERSION
from elasticsearch import Elasticsearch
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
}

# Metrics

_base_scoped_metrics = (("Datastore/statement/Elasticsearch/contacts/index", 2),)

_base_rollup_metrics = (
    ("Datastore/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/Elasticsearch/all", 2),
    ("Datastore/Elasticsearch/allOther", 2),
    ("Datastore/operation/Elasticsearch/index", 2),
    ("Datastore/statement/Elasticsearch/contacts/index", 2),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

if len(ES_MULTIPLE_SETTINGS) > 1:
    es_1 = ES_MULTIPLE_SETTINGS[0]
    es_2 = ES_MULTIPLE_SETTINGS[1]

    host_1 = instance_hostname(es_1["host"])
    port_1 = es_1["port"]

    host_2 = instance_hostname(es_2["host"])
    port_2 = es_2["port"]

    instance_metric_name_1 = "Datastore/instance/Elasticsearch/%s/%s" % (host_1, port_1)
    instance_metric_name_2 = "Datastore/instance/Elasticsearch/%s/%s" % (host_2, port_2)

    _enable_rollup_metrics.extend(
        [
            (instance_metric_name_1, 1),
            (instance_metric_name_2, 1),
        ]
    )

    _disable_rollup_metrics.extend(
        [
            (instance_metric_name_1, None),
            (instance_metric_name_2, None),
        ]
    )

# Query


def _exercise_es(es):
    if ES_VERSION >= (8,):
        es.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1)
    else:
        es.index(
            index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Engineer"}, id=1
        )


# Test


@pytest.mark.skipif(len(ES_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_dbs_enabled",
    scoped_metrics=_enable_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_dbs_enabled():
    for db in ES_MULTIPLE_SETTINGS:
        es_url = "http://%s:%s" % (db["host"], db["port"])
        client = Elasticsearch(es_url)
        _exercise_es(client)


@pytest.mark.skipif(len(ES_MULTIPLE_SETTINGS) < 2, reason="Test environment not configured with multiple databases.")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_multiple_dbs:test_multiple_dbs_disabled",
    scoped_metrics=_disable_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_multiple_dbs_disabled():
    for db in ES_MULTIPLE_SETTINGS:
        es_url = "http://%s:%s" % (db["host"], db["port"])
        client = Elasticsearch(es_url)
        _exercise_es(client)
