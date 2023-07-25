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
    italy_doc = collection.document("Italy")
    italy_doc.set({"capital": "Rome", "currency": "Euro", "language": "Italian"})
    italy_doc.get()
    italian_cities = italy_doc.collection("cities")
    italian_cities.add({"capital": "Rome"})
    retrieved_coll = list(italy_doc.collections())
    assert len(retrieved_coll) == 1

    usa_doc = collection.document("USA")
    usa_doc.create({"capital": "Washington D.C.", "currency": "Dollar", "language": "English"})
    usa_doc.update({"president": "Joe Biden"})

    collection.document("USA").delete()


def test_firestore_documents(collection):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/Italy/set", 1),
        ("Datastore/statement/Firestore/Italy/get", 1),
        ("Datastore/statement/Firestore/Italy/collections", 1),
        ("Datastore/statement/Firestore/cities/add", 1),
        ("Datastore/statement/Firestore/USA/create", 1),
        ("Datastore/statement/Firestore/USA/update", 1),
        ("Datastore/statement/Firestore/USA/delete", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/set", 1),
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/add", 1),
        ("Datastore/operation/Firestore/collections", 1),
        ("Datastore/operation/Firestore/create", 1),
        ("Datastore/operation/Firestore/update", 1),
        ("Datastore/operation/Firestore/delete", 1),
        ("Datastore/all", 7),
        ("Datastore/allOther", 7),
    ]
    @validate_transaction_metrics(
        "test_firestore_documents",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_documents")
    def _test():
        _exercise_firestore(collection)

    _test()


@background_task()
def test_firestore_documents_generators(collection, assert_trace_for_generator):
    subcollection_doc = collection.document("SubCollections")
    subcollection_doc.set({})
    subcollection_doc.collection("collection1").add({})
    subcollection_doc.collection("collection2").add({})
    assert len(list(subcollection_doc.collections())) == 2
    
    assert_trace_for_generator(subcollection_doc.collections)


@validate_database_duration()
@background_task()
def test_firestore_documents_db_duration(collection):
    _exercise_firestore(collection)
