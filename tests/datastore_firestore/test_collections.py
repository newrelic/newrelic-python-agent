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
from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)
from testing_support.validators.validate_tt_collector_json import (
    validate_tt_collector_json,
)

from newrelic.api.background_task import background_task


@pytest.fixture()
def exercise_collections(collection):
    def _exercise_collections():
        collection.document("DoesNotExist")
        collection.add({"capital": "Rome", "currency": "Euro", "language": "Italian"}, "Italy")
        collection.add({"capital": "Mexico City", "currency": "Peso", "language": "Spanish"}, "Mexico")

        documents_get = collection.get()
        assert len(documents_get) == 2
        documents_stream = [_ for _ in collection.stream()]
        assert len(documents_stream) == 2
        documents_list = [_ for _ in collection.list_documents()]
        assert len(documents_list) == 2

    return _exercise_collections


def test_firestore_collections(exercise_collections, collection, instance_info):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/%s/stream" % collection.id, 1),
        ("Datastore/statement/Firestore/%s/get" % collection.id, 1),
        ("Datastore/statement/Firestore/%s/list_documents" % collection.id, 1),
        ("Datastore/statement/Firestore/%s/add" % collection.id, 2),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/add", 2),
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/operation/Firestore/list_documents", 1),
        ("Datastore/all", 5),
        ("Datastore/allOther", 5),
        ("Datastore/instance/Firestore/%s/%s" % (instance_info["host"], instance_info["port_path_or_id"]), 5),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_collections",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_collections")
    def _test():
        exercise_collections()

    _test()


@background_task()
def test_firestore_collections_generators(collection, assert_trace_for_generator):
    collection.add({})
    collection.add({})
    assert len([_ for _ in collection.list_documents()]) == 2

    assert_trace_for_generator(collection.stream)
    assert_trace_for_generator(collection.list_documents)


def test_firestore_collections_trace_node_datastore_params(exercise_collections, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        exercise_collections()

    _test()
