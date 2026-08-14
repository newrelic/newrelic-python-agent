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
from testing_support.db_settings import cosmos_settings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

from newrelic.common.package_version_utils import get_package_version_tuple

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
    app_name="Python Agent Test (datastore_cosmosdb)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)

DB_SETTINGS = cosmos_settings()[0]
COSMOSDB_VERSION = get_package_version_tuple("azure-cosmos")


@pytest.fixture
def client():
    import azure.cosmos

    client = azure.cosmos.CosmosClient(
        url=DB_SETTINGS["url"],
        credential=DB_SETTINGS["credential"],
    )

    yield client
    client.close()


@pytest.fixture
def async_client(loop):
    import azure.cosmos.aio

    async_client = azure.cosmos.aio.CosmosClient(
        url=DB_SETTINGS["url"],
        credential=DB_SETTINGS["credential"],
    )

    yield async_client
    loop.run_until_complete(async_client.close())


@pytest.fixture
def database(client):
    database = client.create_database_if_not_exists("test_database")

    yield database
    client.delete_database("test_database")


@pytest.fixture
def async_database(loop, async_client):
    async_database = loop.run_until_complete(
        async_client.create_database_if_not_exists("test_database")
    )

    yield async_database
    loop.run_until_complete(async_client.delete_database("test_database"))


@pytest.fixture
def container(database):
    import azure.cosmos

    container = database.create_container_if_not_exists(
        "test_container",
        partition_key=azure.cosmos.PartitionKey(path="/container"),
    )

    yield container
    database.delete_container("test_container")


@pytest.fixture
def async_container(loop, async_database):
    import azure.cosmos

    async_container = loop.run_until_complete(
        async_database.create_container_if_not_exists(
            "test_container",
            partition_key=azure.cosmos.PartitionKey(path="/container"),
        )
    )

    yield async_container
    loop.run_until_complete(async_database.delete_container("test_container"))


@pytest.fixture
def user(database):
    user = database.create_user({"id": "test_user"})

    yield user
    database.delete_user("test_user")


@pytest.fixture
def async_user(loop, async_database):
    user = loop.run_until_complete(
        async_database.create_user({"id": "test_user"})
    )

    yield user
    loop.run_until_complete(async_database.delete_user("test_user"))


@pytest.fixture
def item(container):
    body = {"id": "test_item", "container": "test_partition", "value": 42}
    result = container.create_item(body)
    
    yield result

    try:
        container.delete_item("test_item", partition_key="test_partition")
    except Exception:
        pass


@pytest.fixture
def async_item(loop, async_container):
    body = {"id": "test_item", "container": "test_partition", "value": 42}
    result = loop.run_until_complete(async_container.create_item(body))

    yield result

    try:
        loop.run_until_complete(async_container.delete_item("test_item", partition_key="test_partition"))
    except Exception:
        pass


@pytest.fixture
def permission(user, container):
    body = {"id": "test_permission", "permissionMode": "Read", "resource": container.container_link}
    result = user.create_permission(body)
    
    yield result

    try:
        user.delete_permission("test_permission")
    except Exception:
        pass


@pytest.fixture
def async_permission(loop, async_user, async_container):
    body = {"id": "test_permission", "permissionMode": "Read", "resource": async_container.container_link}
    result = loop.run_until_complete(async_user.create_permission(body))

    yield result

    try:
        loop.run_until_complete(async_user.delete_permission("test_permission"))
    except Exception:
        pass

