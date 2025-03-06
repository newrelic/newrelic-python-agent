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
    for x in range(1, 4):
        collection.add({"x": x}, f"doc{x}")


@pytest.fixture()
def exercise_async_transaction_commit(async_client, async_collection):
    async def _exercise_async_transaction_commit():
        from google.cloud.firestore import async_transactional

        @async_transactional
        async def _exercise(async_transaction):
            # get a DocumentReference
            with pytest.raises(
                TypeError
            ):  # get is currently broken. It attempts to await an async_generator instead of consuming it.
                [_ async for _ in async_transaction.get(async_collection.document("doc1"))]

            # get a Query
            with pytest.raises(
                TypeError
            ):  # get is currently broken. It attempts to await an async_generator instead of consuming it.
                async_query = async_collection.select("x").where(field_path="x", op_string=">", value=2)
                assert len([_ async for _ in async_transaction.get(async_query)]) == 1

            # get_all on a list of DocumentReferences
            with pytest.raises(
                TypeError
            ):  # get_all is currently broken. It attempts to await an async_generator instead of consuming it.
                all_docs = async_transaction.get_all([async_collection.document(f"doc{x}") for x in range(1, 4)])
                assert len([_ async for _ in all_docs]) == 3

            # set and delete methods
            async_transaction.set(async_collection.document("doc2"), {"x": 0})
            async_transaction.delete(async_collection.document("doc3"))

        await _exercise(async_client.transaction())
        assert len([_ async for _ in async_collection.list_documents()]) == 2

    return _exercise_async_transaction_commit


@pytest.fixture()
def exercise_async_transaction_rollback(async_client, async_collection):
    async def _exercise_async_transaction_rollback():
        from google.cloud.firestore import async_transactional

        @async_transactional
        async def _exercise(async_transaction):
            # set and delete methods
            async_transaction.set(async_collection.document("doc2"), {"x": 99})
            async_transaction.delete(async_collection.document("doc1"))
            raise RuntimeError

        with pytest.raises(RuntimeError):
            await _exercise(async_client.transaction())
        assert len([_ async for _ in async_collection.list_documents()]) == 3

    return _exercise_async_transaction_rollback


def test_firestore_async_transaction_commit(loop, exercise_async_transaction_commit, async_collection, instance_info):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/commit", 1),
        # ("Datastore/operation/Firestore/get_all", 2),
        # (f"Datastore/statement/Firestore/{async_collection.id}/stream", 1),
        (f"Datastore/statement/Firestore/{async_collection.id}/list_documents", 1),
    ]

    _test_rollup_metrics = [
        # ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/operation/Firestore/list_documents", 1),
        ("Datastore/all", 2),  # Should be 5 if not for broken APIs
        ("Datastore/allOther", 2),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 2),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_transaction",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_transaction")
    def _test():
        loop.run_until_complete(exercise_async_transaction_commit())

    _test()


def test_firestore_async_transaction_rollback(
    loop, exercise_async_transaction_rollback, async_collection, instance_info
):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/rollback", 1),
        (f"Datastore/statement/Firestore/{async_collection.id}/list_documents", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/list_documents", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 2),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_transaction",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_transaction")
    def _test():
        loop.run_until_complete(exercise_async_transaction_rollback())

    _test()


def test_firestore_async_transaction_commit_trace_node_datastore_params(
    loop, exercise_async_transaction_commit, instance_info
):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_transaction_commit())

    _test()


def test_firestore_async_transaction_rollback_trace_node_datastore_params(
    loop, exercise_async_transaction_rollback, instance_info
):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_transaction_rollback())

    _test()
