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

import psycopg
from conftest import DB_SETTINGS, maybe_await
from testing_support.fixtures import override_application_settings, validate_tt_parenting
from testing_support.util import instance_hostname
from testing_support.validators.validate_tt_collector_json import validate_tt_collector_json

from newrelic.api.background_task import background_task

# Settings

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
    "datastore_tracer.database_name_reporting.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
    "datastore_tracer.database_name_reporting.enabled": False,
}

# Expected parameters

_enabled_required = {
    "host": instance_hostname(DB_SETTINGS["host"]),
    "port_path_or_id": str(DB_SETTINGS["port"]),
    "db.instance": DB_SETTINGS["name"],
}
_enabled_forgone = {}

_disabled_required = {}
_disabled_forgone = {"host": "VALUE NOT USED", "port_path_or_id": "VALUE NOT USED", "db.instance": "VALUE NOT USED"}

_tt_parenting = ("TransactionNode", [("FunctionNode", []), ("DatabaseNode", [])])


# Query


async def _exercise_db(async_=False):
    # Connect here without using fixture to assert on the parenting of the FunctionTrace for Connection.connect()
    # This is only possible when the connection is done inside a transaction, so connect after the test starts.
    connect = psycopg.Connection.connect if async_ else psycopg.AsyncConnection.connect
    connection = await maybe_await(
        connect(
            dbname=DB_SETTINGS["name"],
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
        )
    )

    try:
        cursor = connection.cursor()
        await maybe_await(cursor.execute("SELECT setting from pg_settings where name=%s", ("server_version",)))
    finally:
        await maybe_await(connection.close())


# Tests


@override_application_settings(_enable_instance_settings)
@validate_tt_collector_json(datastore_params=_enabled_required, datastore_forgone_params=_enabled_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_enable_instance(loop, is_async):
    loop.run_until_complete(_exercise_db(is_async))


@override_application_settings(_disable_instance_settings)
@validate_tt_collector_json(datastore_params=_disabled_required, datastore_forgone_params=_disabled_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_disable_instance(loop, is_async):
    loop.run_until_complete(_exercise_db(is_async))
