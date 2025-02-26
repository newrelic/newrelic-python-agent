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
from testing_support.validators.validate_database_duration import validate_database_duration
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_tt_collector_json import validate_tt_collector_json

from newrelic.api.background_task import background_task


@pytest.fixture(autouse=True)
def sample_data(collection):
    for x in range(1, 6):
        collection.add({"x": x})

    subcollection_doc = collection.document("subcollection")
    subcollection_doc.set({})
    subcollection_doc.collection("subcollection1").add({})


# ===== AsyncQuery =====


@pytest.fixture()
def exercise_async_query(async_collection):
    async def _exercise_async_query():
        async_query = (
            async_collection.select("x").limit(10).order_by("x").where(field_path="x", op_string="<=", value=3)
        )
        assert len(await async_query.get()) == 3
        assert len([_ async for _ in async_query.stream()]) == 3

    return _exercise_async_query


def test_firestore_async_query(loop, exercise_async_query, async_collection, instance_info):
    _test_scoped_metrics = [
        (f"Datastore/statement/Firestore/{async_collection.id}/stream", 1),
        (f"Datastore/statement/Firestore/{async_collection.id}/get", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 2),
    ]

    # @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_query",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_query")
    def _test():
        loop.run_until_complete(exercise_async_query())

    _test()


@background_task()
def test_firestore_async_query_generators(async_collection, assert_trace_for_async_generator):
    async_query = async_collection.select("x").where(field_path="x", op_string="<=", value=3)
    assert_trace_for_async_generator(async_query.stream)


def test_firestore_async_query_trace_node_datastore_params(loop, exercise_async_query, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_query())

    _test()


# ===== AsyncAggregationQuery =====


@pytest.fixture()
def exercise_async_aggregation_query(async_collection):
    async def _exercise_async_aggregation_query():
        async_aggregation_query = async_collection.select("x").where(field_path="x", op_string="<=", value=3).count()
        assert (await async_aggregation_query.get())[0][0].value == 3
        assert [_ async for _ in async_aggregation_query.stream()][0][0].value == 3

    return _exercise_async_aggregation_query


def test_firestore_async_aggregation_query(loop, exercise_async_aggregation_query, async_collection, instance_info):
    _test_scoped_metrics = [
        (f"Datastore/statement/Firestore/{async_collection.id}/stream", 1),
        (f"Datastore/statement/Firestore/{async_collection.id}/get", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 2),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_aggregation_query",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_aggregation_query")
    def _test():
        loop.run_until_complete(exercise_async_aggregation_query())

    _test()


@background_task()
def test_firestore_async_aggregation_query_generators(async_collection, assert_trace_for_async_generator):
    async_aggregation_query = async_collection.select("x").where(field_path="x", op_string="<=", value=3).count()
    assert_trace_for_async_generator(async_aggregation_query.stream)


def test_firestore_async_aggregation_query_trace_node_datastore_params(
    loop, exercise_async_aggregation_query, instance_info
):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_aggregation_query())

    _test()


# ===== CollectionGroup =====


@pytest.fixture()
def patch_partition_queries(monkeypatch, async_client, collection, sample_data):
    """
    Partitioning is not implemented in the Firestore emulator.

    Ordinarily this method would return a coroutine that returns an async_generator of Cursor objects.
    Each Cursor must point at a valid document path. To test this, we can patch the RPC to return 1 Cursor
    which is pointed at any document available. The get_partitions will take that and make 2 QueryPartition
    objects out of it, which should be enough to ensure we can exercise the generator's tracing.
    """
    from google.cloud.firestore_v1.types.document import Value
    from google.cloud.firestore_v1.types.query import Cursor

    subcollection = collection.document("subcollection").collection("subcollection1")
    documents = [d for d in subcollection.list_documents()]

    async def mock_partition_query(*args, **kwargs):
        async def _mock_partition_query():
            yield Cursor(before=False, values=[Value(reference_value=documents[0].path)])

        return _mock_partition_query()

    monkeypatch.setattr(async_client._firestore_api, "partition_query", mock_partition_query)
    yield


@pytest.fixture()
def exercise_async_collection_group(async_client, async_collection):
    async def _exercise_async_collection_group():
        async_collection_group = async_client.collection_group(async_collection.id)
        assert len(await async_collection_group.get())
        assert len([d async for d in async_collection_group.stream()])

        partitions = [p async for p in async_collection_group.get_partitions(1)]
        assert len(partitions) == 2
        documents = []
        while partitions:
            documents.extend(await partitions.pop().query().get())
        assert len(documents) == 6

    return _exercise_async_collection_group


def test_firestore_async_collection_group(
    loop, exercise_async_collection_group, async_collection, patch_partition_queries, instance_info
):
    _test_scoped_metrics = [
        (f"Datastore/statement/Firestore/{async_collection.id}/get", 3),
        (f"Datastore/statement/Firestore/{async_collection.id}/stream", 1),
        (f"Datastore/statement/Firestore/{async_collection.id}/get_partitions", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 3),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/operation/Firestore/get_partitions", 1),
        ("Datastore/all", 5),
        ("Datastore/allOther", 5),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 5),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_collection_group",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_collection_group")
    def _test():
        loop.run_until_complete(exercise_async_collection_group())

    _test()


@background_task()
def test_firestore_async_collection_group_generators(
    async_client, async_collection, assert_trace_for_async_generator, patch_partition_queries
):
    async_collection_group = async_client.collection_group(async_collection.id)
    assert_trace_for_async_generator(async_collection_group.get_partitions, 1)


def test_firestore_async_collection_group_trace_node_datastore_params(
    loop, exercise_async_collection_group, instance_info, patch_partition_queries
):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_collection_group())

    _test()
