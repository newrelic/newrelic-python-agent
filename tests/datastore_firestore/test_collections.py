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

from newrelic.api.time_trace import current_trace
from newrelic.api.datastore_trace import DatastoreTrace
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task
from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)


def _exercise_firestore(collection):
    collection.document("DoesNotExist")
    collection.add({"capital": "Rome", "currency": "Euro", "language": "Italian"}, "Italy")
    collection.add({"capital": "Mexico City", "currency": "Peso", "language": "Spanish"}, "Mexico")
    
    documents_get = collection.get()
    assert len(documents_get) == 2
    documents_stream = list(collection.stream())
    assert len(documents_stream) == 2
    documents_list = list(collection.list_documents())
    assert len(documents_list) == 2


def test_firestore_collections(collection):
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
    ]
    @validate_transaction_metrics(
        "test_firestore_collections",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_collections")
    def _test():
        _exercise_firestore(collection)

    _test()


@background_task()
def test_firestore_collections_generators(collection):
    txn = current_trace()
    collection.add({})
    collection.add({})
    assert len(list(collection.list_documents())) == 2
    
    # Check for generator trace on stream
    _trace_check = []
    for _ in collection.stream():
        _trace_check.append(isinstance(current_trace(), DatastoreTrace))
    assert _trace_check and all(_trace_check)
    assert current_trace() is txn

    # Check for generator trace on list_documents
    _trace_check = []
    for _ in collection.list_documents():
        _trace_check.append(isinstance(current_trace(), DatastoreTrace))
    assert _trace_check and all(_trace_check)
    assert current_trace() is txn


@validate_database_duration()
@background_task()
def test_firestore_collections_db_duration(collection):
    _exercise_firestore(collection)
