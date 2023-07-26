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

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task
from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)


async def _exercise_collections(async_collection):
    async_collection.document("DoesNotExist")
    await async_collection.add({"capital": "Rome", "currency": "Euro", "language": "Italian"}, "Italy")
    await async_collection.add({"capital": "Mexico City", "currency": "Peso", "language": "Spanish"}, "Mexico")
    
    documents_get = await async_collection.get()
    assert len(documents_get) == 2
    documents_stream = [_ async for _ in async_collection.stream()]
    assert len(documents_stream) == 2
    documents_list = [_ async for _ in async_collection.list_documents()]
    assert len(documents_list) == 2


def test_firestore_async_collections(loop, async_collection):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/%s/stream" % async_collection.id, 1),
        ("Datastore/statement/Firestore/%s/get" % async_collection.id, 1),
        ("Datastore/statement/Firestore/%s/list_documents" % async_collection.id, 1),
        ("Datastore/statement/Firestore/%s/add" % async_collection.id, 2),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/add", 2),
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/operation/Firestore/list_documents", 1),
        ("Datastore/all", 5),
        ("Datastore/allOther", 5),
    ]
    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_collections",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_collections")
    def _test():
        loop.run_until_complete(_exercise_collections(async_collection))

    _test()


@background_task()
def test_firestore_async_collections_generators(loop, collection, async_collection, assert_trace_for_async_generator):
    collection.add({})
    collection.add({})
    assert len([_ for _ in collection.list_documents()]) == 2
    
    assert_trace_for_async_generator(async_collection.stream)
    assert_trace_for_async_generator(async_collection.list_documents)
