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

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task
from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)


@pytest.fixture(autouse=True)
def sample_data(collection):
    for x in range(1, 6):
        collection.add({"x": x})

    subcollection_doc = collection.document("subcollection")
    subcollection_doc.set({})
    subcollection_doc.collection("subcollection1").add({})


# ===== AsyncQuery =====

async def _exercise_async_query(async_collection):
    async_query = async_collection.select("x").limit(10).order_by("x").where(field_path="x", op_string="<=", value=3)
    assert len(await async_query.get()) == 3
    assert len([_ async for _ in async_query.stream()]) == 3


def test_firestore_async_query(loop, async_collection):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/%s/stream" % async_collection.id, 1),
        ("Datastore/statement/Firestore/%s/get" % async_collection.id, 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
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
        loop.run_until_complete(_exercise_async_query(async_collection))

    _test()


@background_task()
def test_firestore_async_query_generators(async_collection, assert_trace_for_async_generator):
    async_query = async_collection.select("x").where(field_path="x", op_string="<=", value=3)
    assert_trace_for_async_generator(async_query.stream)

# ===== AsyncAggregationQuery =====

async def _exercise_async_aggregation_query(async_collection):
    async_aggregation_query = async_collection.select("x").where(field_path="x", op_string="<=", value=3).count()
    assert (await async_aggregation_query.get())[0][0].value == 3
    assert [_ async for _ in async_aggregation_query.stream()][0][0].value == 3


def test_firestore_async_aggregation_query(loop, async_collection):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/%s/stream" % async_collection.id, 1),
        ("Datastore/statement/Firestore/%s/get" % async_collection.id, 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
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
        loop.run_until_complete(_exercise_async_aggregation_query(async_collection))

    _test()


@background_task()
def test_firestore_async_aggregation_query_generators(async_collection, assert_trace_for_async_generator):
    async_aggregation_query = async_collection.select("x").where(field_path="x", op_string="<=", value=3).count()
    assert_trace_for_async_generator(async_aggregation_query.stream)


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


async def _exercise_async_collection_group(async_client, async_collection):
    async_collection_group = async_client.collection_group(async_collection.id)
    assert len(await async_collection_group.get())
    assert len([d async for d in async_collection_group.stream()])

    partitions = [p async for p in async_collection_group.get_partitions(1)]
    assert len(partitions) == 2
    documents = []
    while partitions:
        documents.extend(await partitions.pop().query().get())
    assert len(documents) == 6


def test_firestore_async_collection_group(loop, async_client, async_collection, patch_partition_queries):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/%s/get" % async_collection.id, 3),
        ("Datastore/statement/Firestore/%s/stream" % async_collection.id, 1),
        ("Datastore/statement/Firestore/%s/get_partitions" % async_collection.id, 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 3),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/operation/Firestore/get_partitions", 1),
        ("Datastore/all", 5),
        ("Datastore/allOther", 5),
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
        loop.run_until_complete(_exercise_async_collection_group(async_client, async_collection))

    _test()


@background_task()
def test_firestore_async_collection_group_generators(async_client, async_collection, assert_trace_for_async_generator, patch_partition_queries):
    async_collection_group = async_client.collection_group(async_collection.id)
    assert_trace_for_async_generator(async_collection_group.get_partitions, 1)
