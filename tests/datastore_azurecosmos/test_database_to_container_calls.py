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


def test_database_calls_to_container(database, container):
    container_client = database.get_container_client("test_container")
    assert container_client.id == container.id

    database.create_container("another_container", partition_key=PartitionKey(path="/id"))
    all_containers = database.list_containers()

    container_ids = {container_dict.get("id") for container_dict in all_containers}
    assert container_ids == {"test_container", "another_container"}

    database.delete_container("another_container")
    database.replace_container(
        container,
        partition_key=PartitionKey(path="/new-and-improved-container"),
    )


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
            async_container,
            partition_key=PartitionKey(path="/new-and-improved-container"),
        )

    loop.run_until_complete(_test_async_database_calls_to_container())


def test_database_container_queries(database):
    database.create_container_if_not_exists("test_container", partition_key=PartitionKey(path="/container"))
    results = list(database.query_containers("SELECT * FROM c WHERE c.id = 'test_container'"))
    assert any(c.get("id") == "test_container" for c in results)


def test_container_throughput_and_offer(database):
    container = database.create_container(
        "throughput_container",
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400,
    )
    try:
        throughput = container.get_throughput()
        container.replace_throughput(throughput.offer_throughput + 100)
        container.read_offer()
    finally:
        database.delete_container("throughput_container")


def test_async_container_throughput(loop, async_database):
    async def _test_async_container_throughput():
        container = await async_database.create_container(
            "throughput_container",
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400,
        )
        try:
            throughput = await container.get_throughput()
            await container.replace_throughput(throughput.offer_throughput + 100)
        finally:
            await async_database.delete_container("throughput_container")

    loop.run_until_complete(_test_async_container_throughput())