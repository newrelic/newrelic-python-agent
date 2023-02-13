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

from testing_support.fixtures import (
    override_application_settings,
    validate_tt_parenting,
)
from testing_support.util import instance_hostname
from testing_support.validators.validate_tt_collector_json import (
    validate_tt_collector_json,
)

from newrelic.api.background_task import background_task

from conftest import ES_SETTINGS, ES_VERSION

# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
    "datastore_tracer.database_name_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
    "datastore_tracer.database_name_reporting.enabled": False,
}
_instance_only_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
    "datastore_tracer.database_name_reporting.enabled": False,
}

# Expected parameters

_enabled_required = {
    "host": instance_hostname(ES_SETTINGS["host"]),
    "port_path_or_id": str(ES_SETTINGS["port"]),
}
_enabled_forgone = {
    "db.instance": "VALUE NOT USED",
}

_disabled_required = {}
_disabled_forgone = {
    "host": "VALUE NOT USED",
    "port_path_or_id": "VALUE NOT USED",
    "db.instance": "VALUE NOT USED",
}

_instance_only_required = {
    "host": instance_hostname(ES_SETTINGS["host"]),
    "port_path_or_id": str(ES_SETTINGS["port"]),
}
_instance_only_forgone = {
    "db.instance": "VALUE NOT USED",
}

_tt_parenting = (
    "TransactionNode",
    [
        ("DatastoreNode", []),
    ],
)


# Query


def _exercise_es_v7(es):
    es.index(index="contacts", doc_type="person", body={"name": "Joe Tester", "age": 25, "title": "QA Master"}, id=1)


def _exercise_es_v8(es):
    es.index(index="contacts", body={"name": "Joe Tester", "age": 25, "title": "QA Master"}, id=1)


_exercise_es = _exercise_es_v7 if ES_VERSION < (8, 0, 0) else _exercise_es_v8

# Tests


@override_application_settings(_enable_instance_settings)
@validate_tt_collector_json(datastore_params=_enabled_required, datastore_forgone_params=_enabled_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_enable_instance(client):
    _exercise_es(client)


@override_application_settings(_disable_instance_settings)
@validate_tt_collector_json(datastore_params=_disabled_required, datastore_forgone_params=_disabled_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_disable_instance(client):
    _exercise_es(client)


@override_application_settings(_instance_only_settings)
@validate_tt_collector_json(datastore_params=_instance_only_required, datastore_forgone_params=_instance_only_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_instance_only(client):
    _exercise_es(client)
