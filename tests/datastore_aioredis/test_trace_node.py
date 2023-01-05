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

# import aioredis
# import pytest
# from conftest import AIOREDIS_VERSION, event_loop
from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_tt_collector_json import (
    validate_tt_collector_json,
)

from newrelic.api.background_task import background_task

DB_SETTINGS = redis_settings()[0]

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
_database_only_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
    "datastore_tracer.database_name_reporting.enabled": True,
}


_enabled_required = {
    "host": instance_hostname(DB_SETTINGS["host"]),
    "port_path_or_id": str(DB_SETTINGS["port"]),
    "db.instance": "0",
}
_enabled_forgone = {}

_disabled_required = {}
_disabled_forgone = {
    "host": "VALUE NOT USED",
    "port_path_or_id": "VALUE NOT USED",
    "db.instance": "VALUE NOT USED",
}


_instance_only_required = {
    "host": instance_hostname(DB_SETTINGS["host"]),
    "port_path_or_id": str(DB_SETTINGS["port"]),
}
_instance_only_forgone = {
    "db.instance": "0",
}

_database_only_required = {
    "db.instance": "0",
}
_database_only_forgone = {
    "host": "VALUE NOT USED",
    "port_path_or_id": "VALUE NOT USED",
}


async def exercise_redis(client):
    await client.set("key", "value")
    await client.get("key")

    if hasattr(client, "execute_command"):
        await client.execute_command("CLIENT", "LIST", parse="LIST")
    else:
        await client.execute("CLIENT", "LIST")


@override_application_settings(_enable_instance_settings)
@validate_tt_collector_json(datastore_params=_enabled_required, datastore_forgone_params=_enabled_forgone)
@background_task()
def test_trace_node_datastore_params_enable_instance(client, loop):
    loop.run_until_complete(exercise_redis(client))


@override_application_settings(_disable_instance_settings)
@validate_tt_collector_json(datastore_params=_disabled_required, datastore_forgone_params=_disabled_forgone)
@background_task()
def test_trace_node_datastore_params_disable_instance(client, loop):
    loop.run_until_complete(exercise_redis(client))


@override_application_settings(_instance_only_settings)
@validate_tt_collector_json(datastore_params=_instance_only_required, datastore_forgone_params=_instance_only_forgone)
@background_task()
def test_trace_node_datastore_params_instance_only(client, loop):
    loop.run_until_complete(exercise_redis(client))


@override_application_settings(_database_only_settings)
@validate_tt_collector_json(datastore_params=_database_only_required, datastore_forgone_params=_database_only_forgone)
@background_task()
def test_trace_node_datastore_params_database_only(client, loop):
    loop.run_until_complete(exercise_redis(client))
