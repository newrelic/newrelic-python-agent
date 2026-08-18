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

from conftest import db_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

_base_container_read = (
    ("Datastore/all", 1),
    ("Datastore/CosmosDB/all", 1),
    ("Datastore/allOther", 1),
    ("Datastore/CosmosDB/allOther", 1),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 1),
)

_scoped_container_read = (("Datastore/operation/CosmosDB/read", 1),)


@validate_transaction_metrics(
    "test_container_calls:test_container_read",
    scoped_metrics=_scoped_container_read,
    rollup_metrics=[*_scoped_container_read, *_base_container_read],
    background_task=True,
)
@background_task()
def test_container_read(container):
    props = container.read()
    assert props.get("id") == "test_container"


@validate_transaction_metrics(
    "test_container_calls:test_async_container_read",
    scoped_metrics=_scoped_container_read,
    rollup_metrics=[*_scoped_container_read, *_base_container_read],
    background_task=True,
)
@background_task()
def test_async_container_read(loop, async_container):
    async def _test_async_container_read():
        props = await async_container.read()
        assert props.get("id") == "test_container"

    loop.run_until_complete(_test_async_container_read())


_base_container_item = (
    ("Datastore/all", 6),
    ("Datastore/CosmosDB/all", 6),
    ("Datastore/allOther", 6),
    ("Datastore/CosmosDB/allOther", 6),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 6),
)

_scoped_container_item = (
    ("Datastore/operation/CosmosDB/create_item", 1),
    ("Datastore/operation/CosmosDB/read_item", 1),
    ("Datastore/operation/CosmosDB/replace_item", 1),
    ("Datastore/operation/CosmosDB/upsert_item", 1),
    ("Datastore/operation/CosmosDB/query_items_change_feed", 1),
    ("Datastore/operation/CosmosDB/delete_item", 1),
)


@validate_transaction_metrics(
    "test_container_calls:test_container_item_crud",
    scoped_metrics=_scoped_container_item,
    rollup_metrics=[*_scoped_container_item, *_base_container_item],
    background_task=True,
)
@background_task()
def test_container_item_crud(container, item):
    body = {"id": "crud_item", "container": "part1", "value": 1}
    container.create_item(body)
    container.read_item("crud_item", partition_key="part1")
    container.replace_item("crud_item", {**body, "value": 2})
    container.upsert_item({**body, "value": 3})

    item_generator = container.query_items_change_feed(partition_key="test_partition", start_time="Beginning")
    item_list = [_item.get("id") for _item in item_generator]  # Use list instead of set--order matters
    assert item_list == ["test_item", "crud_item"]

    container.delete_item("crud_item", partition_key="part1")


@validate_transaction_metrics(
    "test_container_calls:test_async_container_item_crud",
    scoped_metrics=_scoped_container_item,
    rollup_metrics=[*_scoped_container_item, *_base_container_item],
    background_task=True,
)
@background_task()
def test_async_container_item_crud(loop, async_container, async_item):
    async def _test_async_container_item_crud():
        body = {"id": "crud_item", "container": "part1", "value": 1}
        await async_container.create_item(body)
        await async_container.read_item("crud_item", partition_key="part1")
        await async_container.replace_item("crud_item", {**body, "value": 2})
        await async_container.upsert_item({**body, "value": 3})

        item_generator = async_container.query_items_change_feed(partition_key="test_partition", start_time="Beginning")
        item_list = [_item.get("id") async for _item in item_generator]  # Use list instead of set--order matters
        assert item_list == ["test_item", "crud_item"]

        await async_container.delete_item("crud_item", partition_key="part1")

    loop.run_until_complete(_test_async_container_item_crud())


_base_container_read_and_query = (
    ("Datastore/all", 2),
    ("Datastore/CosmosDB/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/CosmosDB/allOther", 2),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 2),
)

_scoped_container_read_and_query = (
    ("Datastore/operation/CosmosDB/read_all_items", 1),
    ("Datastore/operation/CosmosDB/query_items", 1),
)


@validate_transaction_metrics(
    "test_container_calls:test_container_read_all_and_query",
    scoped_metrics=_scoped_container_read_and_query,
    rollup_metrics=[*_scoped_container_read_and_query, *_base_container_read_and_query],
    background_task=True,
)
@background_task()
def test_container_read_all_and_query(container, item):
    all_sync_items = container.read_all_items()
    assert any(item.get("id") == "test_item" for item in all_sync_items)

    results = list(
        container.query_items(
            "SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": "test_item"}],
            enable_cross_partition_query=True,
        )
    )
    assert len(results) == 1


@validate_transaction_metrics(
    "test_container_calls:test_async_container_read_all_and_query",
    scoped_metrics=_scoped_container_read_and_query,
    rollup_metrics=[*_scoped_container_read_and_query, *_base_container_read_and_query],
    background_task=True,
)
@background_task()
def test_async_container_read_all_and_query(loop, async_container, async_item):
    async def _test_async_container_read_all_and_query():
        all_async_items = async_container.read_all_items()
        assert any([item.get("id") == "test_item" async for item in all_async_items])

        results = async_container.query_items(
            "SELECT * FROM c WHERE c.id = @id", parameters=[{"name": "@id", "value": "test_item"}]
        )
        result_list = [result async for result in results]
        assert len(result_list) == 1

    loop.run_until_complete(_test_async_container_read_all_and_query())


_base_container_patch = (
    ("Datastore/all", 1),
    ("Datastore/CosmosDB/all", 1),
    ("Datastore/allOther", 1),
    ("Datastore/CosmosDB/allOther", 1),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 1),
)

_scoped_container_patch = (("Datastore/operation/CosmosDB/patch_item", 1),)


@validate_transaction_metrics(
    "test_container_calls:test_container_patch_item",
    scoped_metrics=_scoped_container_patch,
    rollup_metrics=[*_scoped_container_patch, *_base_container_patch],
    background_task=True,
)
@background_task()
def test_container_patch_item(container, item):
    container.patch_item(
        "test_item", partition_key="test_partition", patch_operations=[{"op": "replace", "path": "/value", "value": 99}]
    )


@validate_transaction_metrics(
    "test_container_calls:test_async_container_patch_item",
    scoped_metrics=_scoped_container_patch,
    rollup_metrics=[*_scoped_container_patch, *_base_container_patch],
    background_task=True,
)
@background_task()
def test_async_container_patch_item(loop, async_container, async_item):
    async def _test_async_container_patch_item():
        await async_container.patch_item(
            "test_item",
            partition_key="test_partition",
            patch_operations=[{"op": "replace", "path": "/value", "value": 99}],
        )

    loop.run_until_complete(_test_async_container_patch_item())


_scoped_container_batch = (("Datastore/operation/CosmosDB/execute_item_batch", 1),)


@validate_transaction_metrics(
    "test_container_calls:test_container_batch_operations",
    scoped_metrics=_scoped_container_batch,
    rollup_metrics=[*_scoped_container_batch, *_base_container_patch],
    background_task=True,
)
@background_task()
def test_container_batch_operations(container):
    batch_ops = [
        ("create", ({"id": "batch_item", "container": "batch_part", "value": 0},)),
        ("delete", ("batch_item",)),
    ]
    container.execute_item_batch(batch_ops, partition_key="batch_part")


@validate_transaction_metrics(
    "test_container_calls:test_async_container_batch_operations",
    scoped_metrics=_scoped_container_batch,
    rollup_metrics=[*_scoped_container_batch, *_base_container_patch],
    background_task=True,
)
@background_task()
def test_async_container_batch_operations(loop, async_container):
    async def _test_async_container_batch_operations():
        batch_ops = [
            ("create", ({"id": "batch_item", "container": "batch_part", "value": 0},)),
            ("delete", ("batch_item",)),
        ]
        await async_container.execute_item_batch(batch_ops, partition_key="batch_part")

    loop.run_until_complete(_test_async_container_batch_operations())


_scoped_container_delete = (("Datastore/operation/CosmosDB/delete_all_items_by_partition_key", 1),)


@validate_transaction_metrics(
    "test_container_calls:test_container_delete_by_partition_key",
    scoped_metrics=_scoped_container_delete,
    rollup_metrics=[*_scoped_container_delete, *_base_container_patch],
    background_task=True,
)
@background_task()
def test_container_delete_by_partition_key(container, item):
    container.delete_all_items_by_partition_key("test_partition")


@validate_transaction_metrics(
    "test_container_calls:test_async_container_delete_by_partition_key",
    scoped_metrics=_scoped_container_delete,
    rollup_metrics=[*_scoped_container_delete, *_base_container_patch],
    background_task=True,
)
@background_task()
def test_async_container_delete_by_partition_key(loop, async_container, async_item):
    async def _test_async_container_delete_by_partition_key():
        await async_container.delete_all_items_by_partition_key("test_partition")

    loop.run_until_complete(_test_async_container_delete_by_partition_key())
