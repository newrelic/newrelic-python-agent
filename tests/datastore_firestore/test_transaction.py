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
def exercise_transaction_commit(client, collection):
    def _exercise_transaction_commit():
        from google.cloud.firestore_v1.transaction import transactional

        @transactional
        def _exercise(transaction):
            # get a DocumentReference
            [_ for _ in transaction.get(collection.document("doc1"))]

            # get a Query
            query = collection.select("x").where(field_path="x", op_string=">", value=2)
            assert len([_ for _ in transaction.get(query)]) == 1

            # get_all on a list of DocumentReferences
            all_docs = transaction.get_all([collection.document(f"doc{x}") for x in range(1, 4)])
            assert len([_ for _ in all_docs]) == 3

            # set and delete methods
            transaction.set(collection.document("doc2"), {"x": 0})
            transaction.delete(collection.document("doc3"))

        _exercise(client.transaction())
        assert len([_ for _ in collection.list_documents()]) == 2

    return _exercise_transaction_commit


@pytest.fixture()
def exercise_transaction_rollback(client, collection):
    def _exercise_transaction_rollback():
        from google.cloud.firestore_v1.transaction import transactional

        @transactional
        def _exercise(transaction):
            # set and delete methods
            transaction.set(collection.document("doc2"), {"x": 99})
            transaction.delete(collection.document("doc1"))
            raise RuntimeError

        with pytest.raises(RuntimeError):
            _exercise(client.transaction())
        assert len([_ for _ in collection.list_documents()]) == 3

    return _exercise_transaction_rollback


def test_firestore_transaction_commit(exercise_transaction_commit, collection, instance_info):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/commit", 1),
        ("Datastore/operation/Firestore/get_all", 2),
        (f"Datastore/statement/Firestore/{collection.id}/stream", 1),
        (f"Datastore/statement/Firestore/{collection.id}/list_documents", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/operation/Firestore/list_documents", 1),
        ("Datastore/all", 5),
        ("Datastore/allOther", 5),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 5),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_transaction",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_transaction")
    def _test():
        exercise_transaction_commit()

    _test()


def test_firestore_transaction_rollback(exercise_transaction_rollback, collection, instance_info):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/rollback", 1),
        (f"Datastore/statement/Firestore/{collection.id}/list_documents", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/list_documents", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 2),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_transaction",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_transaction")
    def _test():
        exercise_transaction_rollback()

    _test()


def test_firestore_transaction_commit_trace_node_datastore_params(exercise_transaction_commit, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        exercise_transaction_commit()

    _test()


def test_firestore_transaction_rollback_trace_node_datastore_params(exercise_transaction_rollback, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        exercise_transaction_rollback()

    _test()
