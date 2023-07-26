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
def sample_data(collection, reset_firestore):
    # reset_firestore must be run before, not after this fixture
    for x in range(1, 6):
        collection.add({"x": x})

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
