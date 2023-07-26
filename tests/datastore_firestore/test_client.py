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

from newrelic.api.time_trace import current_trace
from newrelic.api.datastore_trace import DatastoreTrace
from testing_support.db_settings import firestore_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task
from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)


@pytest.fixture()
def existing_document(collection, reset_firestore):
    # reset_firestore must be run before, not after this fixture
    doc = collection.document("document")
    doc.set({"x": 1})
    return doc


def _exercise_client(client, collection, existing_document):
    assert len([_ for _ in client.collections()]) == 1
    doc = [_ for _ in client.get_all([existing_document])][0]
    assert doc.to_dict()["x"] == 1


def test_firestore_client(client, collection, existing_document):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/collections", 1),
        ("Datastore/operation/Firestore/get_all", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
    ]

    @validate_transaction_metrics(
        "test_firestore_client",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_client")
    def _test():
        _exercise_client(client, collection, existing_document)

    _test()


@background_task()
def test_firestore_client_generators(client, collection, assert_trace_for_generator):
    doc = collection.document("test")
    doc.set({})

    assert_trace_for_generator(client.collections)
    assert_trace_for_generator(client.get_all, [doc])


@validate_database_duration()
@background_task()
def test_firestore_client_db_duration(client, collection, existing_document):
    _exercise_client(client, collection, existing_document)
