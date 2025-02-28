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
def existing_document(collection):
    doc = collection.document("document")
    doc.set({"x": 1})
    return doc


@pytest.fixture()
def exercise_async_client(async_client, existing_document):
    async def _exercise_async_client():
        assert len([_ async for _ in async_client.collections()]) >= 1
        doc = [_ async for _ in async_client.get_all([existing_document])][0]
        assert doc.to_dict()["x"] == 1

    return _exercise_async_client


def test_firestore_async_client(loop, exercise_async_client, instance_info):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/collections", 1),
        ("Datastore/operation/Firestore/get_all", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 2),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_client",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_client")
    def _test():
        loop.run_until_complete(exercise_async_client())

    _test()


@background_task()
def test_firestore_async_client_generators(async_client, collection, assert_trace_for_async_generator):
    doc = collection.document("test")
    doc.set({})

    assert_trace_for_async_generator(async_client.collections)
    assert_trace_for_async_generator(async_client.get_all, [doc])


def test_firestore_async_client_trace_node_datastore_params(loop, exercise_async_client, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_client())

    _test()
