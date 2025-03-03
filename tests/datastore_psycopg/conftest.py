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
from testing_support.db_settings import postgresql_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_explain_plan_queries": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_psycopg)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)


DB_MULTIPLE_SETTINGS = postgresql_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]


@pytest.fixture(scope="session", params=["sync", "async"])
def is_async(request):
    return request.param == "async"


@pytest.fixture(scope="function")
def connection(loop, is_async):
    import psycopg

    if not is_async:
        connection = psycopg.connect(
            dbname=DB_SETTINGS["name"],
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
        )
    else:
        connection = loop.run_until_complete(
            psycopg.AsyncConnection.connect(
                dbname=DB_SETTINGS["name"],
                user=DB_SETTINGS["user"],
                password=DB_SETTINGS["password"],
                host=DB_SETTINGS["host"],
                port=DB_SETTINGS["port"],
            )
        )

    yield connection
    loop.run_until_complete(maybe_await(connection.close()))


@pytest.fixture(scope="function")
def multiple_connections(loop, is_async):
    import psycopg

    if len(DB_MULTIPLE_SETTINGS) < 2:
        pytest.skip(reason="Test environment not configured with multiple databases.")

    connections = []
    for DB_SETTINGS in DB_MULTIPLE_SETTINGS:
        if not is_async:
            connections.append(
                psycopg.connect(
                    dbname=DB_SETTINGS["name"],
                    user=DB_SETTINGS["user"],
                    password=DB_SETTINGS["password"],
                    host=DB_SETTINGS["host"],
                    port=DB_SETTINGS["port"],
                )
            )
        else:
            connections.append(
                loop.run_until_complete(
                    psycopg.AsyncConnection.connect(
                        dbname=DB_SETTINGS["name"],
                        user=DB_SETTINGS["user"],
                        password=DB_SETTINGS["password"],
                        host=DB_SETTINGS["host"],
                        port=DB_SETTINGS["port"],
                    )
                )
            )

    yield connections
    for connection in connections:
        loop.run_until_complete(maybe_await(connection.close()))


async def maybe_await(value):
    if hasattr(value, "__await__"):
        return await value

    return value
