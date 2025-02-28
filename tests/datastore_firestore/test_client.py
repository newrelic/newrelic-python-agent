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
def sample_data(collection):
    doc = collection.document("document")
    doc.set({"x": 1})
    return doc


@pytest.fixture()
def exercise_client(client, sample_data):
    def _exercise_client():
        assert len([_ for _ in client.collections()])
        doc = [_ for _ in client.get_all([sample_data])][0]
        assert doc.to_dict()["x"] == 1

    return _exercise_client


def test_firestore_client(exercise_client, instance_info):
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
        "test_firestore_client",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_client")
    def _test():
        exercise_client()

    _test()


@background_task()
def test_firestore_client_generators(client, sample_data, assert_trace_for_generator):
    assert_trace_for_generator(client.collections)
    assert_trace_for_generator(client.get_all, [sample_data])


def test_firestore_client_trace_node_datastore_params(exercise_client, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        exercise_client()

    _test()
