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


@pytest.fixture()
def exercise_async_documents(async_collection):
    async def _exercise_async_documents():
        italy_doc = async_collection.document("Italy")
        await italy_doc.set({"capital": "Rome", "currency": "Euro", "language": "Italian"})
        await italy_doc.get()
        italian_cities = italy_doc.collection("cities")
        await italian_cities.add({"capital": "Rome"})
        retrieved_coll = [_ async for _ in italy_doc.collections()]
        assert len(retrieved_coll) == 1

        usa_doc = async_collection.document("USA")
        await usa_doc.create({"capital": "Washington D.C.", "currency": "Dollar", "language": "English"})
        await usa_doc.update({"president": "Joe Biden"})

        await async_collection.document("USA").delete()

    return _exercise_async_documents


def test_firestore_async_documents(loop, exercise_async_documents, instance_info):
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
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 7),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_documents",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_documents")
    def _test():
        loop.run_until_complete(exercise_async_documents())

    _test()


@background_task()
def test_firestore_async_documents_generators(
    collection, async_collection, assert_trace_for_async_generator, instance_info
):
    subcollection_doc = collection.document("SubCollections")
    subcollection_doc.set({})
    subcollection_doc.collection("collection1").add({})
    subcollection_doc.collection("collection2").add({})
    assert len([_ for _ in subcollection_doc.collections()]) == 2

    async_subcollection = async_collection.document(subcollection_doc.id)

    assert_trace_for_async_generator(async_subcollection.collections)


def test_firestore_async_documents_trace_node_datastore_params(loop, exercise_async_documents, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_documents())

    _test()
