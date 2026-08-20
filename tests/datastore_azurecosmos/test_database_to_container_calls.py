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

from azure.cosmos import PartitionKey
from conftest import db_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

_base_container_calls = (
    ("Datastore/all", 5),
    ("Datastore/CosmosDB/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/CosmosDB/allOther", 5),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 5),
)

_scoped_container_calls = (
    ("Datastore/operation/CosmosDB/get_container_client", 1),
    ("Datastore/operation/CosmosDB/create_container", 1),
    ("Datastore/operation/CosmosDB/list_containers", 1),
    ("Datastore/operation/CosmosDB/delete_container", 1),
    ("Datastore/operation/CosmosDB/replace_container", 1),
)


@validate_transaction_metrics(
    "test_database_to_container_calls:test_database_calls_to_container",
    scoped_metrics=_scoped_container_calls,
    rollup_metrics=[*_scoped_container_calls, *_base_container_calls],
    background_task=True,
)
@background_task()
def test_database_calls_to_container(database, container):
    container_client = database.get_container_client("test_container")
    assert container_client.id == container.id

    database.create_container("another_container", partition_key=PartitionKey(path="/id"))
    all_containers = database.list_containers()

    container_ids = {container_dict.get("id") for container_dict in all_containers}
    assert container_ids == {"test_container", "another_container"}

    database.delete_container("another_container")
    database.replace_container(container, partition_key=PartitionKey(path="/new-and-improved-container"))


@validate_transaction_metrics(
    "test_database_to_container_calls:test_async_database_calls_to_container",
    scoped_metrics=_scoped_container_calls,
    rollup_metrics=[*_scoped_container_calls, *_base_container_calls],
    background_task=True,
)
@background_task()
def test_async_database_calls_to_container(loop, async_database, async_container):
    async def _test_async_database_calls_to_container():
        container_client = async_database.get_container_client("test_container")
        assert container_client.id == async_container.id

        await async_database.create_container("another_container", partition_key=PartitionKey(path="/id"))
        all_containers = async_database.list_containers()

        container_ids = {container_dict.get("id") async for container_dict in all_containers}
        assert container_ids == {"test_container", "another_container"}

        await async_database.delete_container("another_container")
        await async_database.replace_container(
            async_container, partition_key=PartitionKey(path="/new-and-improved-container")
        )

    loop.run_until_complete(_test_async_database_calls_to_container())


_base_container_query = (
    ("Datastore/all", 2),
    ("Datastore/CosmosDB/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/CosmosDB/allOther", 2),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 2),
)

_scoped_container_query = (
    ("Datastore/operation/CosmosDB/create_container_if_not_exists", 1),
    ("Datastore/operation/CosmosDB/query_containers", 1),
)


@validate_transaction_metrics(
    "test_database_to_container_calls:test_database_container_queries",
    scoped_metrics=_scoped_container_query,
    rollup_metrics=[*_scoped_container_query, *_base_container_query],
    background_task=True,
)
@background_task()
def test_database_container_queries(database):
    database.create_container_if_not_exists("test_container", partition_key=PartitionKey(path="/container"))
    results = database.query_containers("SELECT * FROM c WHERE c.id = 'test_container'")
    assert any(container.get("id") == "test_container" for container in results)


@validate_transaction_metrics(
    "test_database_to_container_calls:test_async_database_container_queries",
    scoped_metrics=_scoped_container_query,
    rollup_metrics=[*_scoped_container_query, *_base_container_query],
    background_task=True,
)
@background_task()
def test_async_database_container_queries(loop, async_database):
    async def _test_async_database_container_queries():
        await async_database.create_container_if_not_exists(
            "test_container", partition_key=PartitionKey(path="/container")
        )
        results = async_database.query_containers("SELECT * FROM c WHERE c.id = 'test_container'")
        assert any([container.get("id") == "test_container" async for container in results])

    loop.run_until_complete(_test_async_database_container_queries())


_base_sync_container_throughput = (
    ("Datastore/all", 5),
    ("Datastore/CosmosDB/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/CosmosDB/allOther", 5),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 5),
)

_scoped_container_throughput = (
    ("Datastore/operation/CosmosDB/create_container", 1),
    ("Datastore/operation/CosmosDB/get_throughput", 1),
    ("Datastore/operation/CosmosDB/replace_throughput", 1),
    ("Datastore/operation/CosmosDB/delete_container", 1),
)

_scoped_sync_container_throughput = (*_scoped_container_throughput, ("Datastore/operation/CosmosDB/read_offer", 1))


@validate_transaction_metrics(
    "test_database_to_container_calls:test_container_throughput_and_offer",
    scoped_metrics=_scoped_sync_container_throughput,
    rollup_metrics=[*_scoped_sync_container_throughput, *_base_sync_container_throughput],
    background_task=True,
)
@background_task()
def test_container_throughput_and_offer(database):
    container = database.create_container(
        "throughput_container", partition_key=PartitionKey(path="/id"), offer_throughput=400
    )
    try:
        throughput = container.get_throughput()
        container.replace_throughput(throughput.offer_throughput + 100)
        container.read_offer()
    finally:
        database.delete_container("throughput_container")


_base_async_container_throughput = (
    ("Datastore/all", 4),
    ("Datastore/CosmosDB/all", 4),
    ("Datastore/allOther", 4),
    ("Datastore/CosmosDB/allOther", 4),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 4),
)


@validate_transaction_metrics(
    "test_database_to_container_calls:test_async_container_throughput",
    scoped_metrics=_scoped_container_throughput,
    rollup_metrics=[*_scoped_container_throughput, *_base_async_container_throughput],
    background_task=True,
)
@background_task()
def test_async_container_throughput(loop, async_database):
    async def _test_async_container_throughput():
        container = await async_database.create_container(
            "throughput_container", partition_key=PartitionKey(path="/id"), offer_throughput=400
        )
        try:
            throughput = await container.get_throughput()
            await container.replace_throughput(throughput.offer_throughput + 100)
        finally:
            await async_database.delete_container("throughput_container")

    loop.run_until_complete(_test_async_container_throughput())
