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

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task
from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)


@pytest.fixture(autouse=True)
def sample_data(collection, reset_firestore):
    # reset_firestore must be run before, not after this fixture
    for x in range(1, 6):
        collection.add({"x": x})


def _exercise_firestore(collection):
    query = collection.select("x").limit(10).order_by("x").where("x", "<=", 3)
    assert len(query.get()) == 3
    assert len(list(query.stream())) == 3


def test_firestore_query(collection):
    _test_scoped_metrics = [
        ("Datastore/statement/Firestore/%s/stream" % collection.id, 1),
        ("Datastore/statement/Firestore/%s/get" % collection.id, 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/operation/Firestore/get", 1),
        ("Datastore/operation/Firestore/stream", 1),
        ("Datastore/all", 2),
        ("Datastore/allOther", 2),
    ]
    @validate_transaction_metrics(
        "test_firestore_query",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_query")
    def _test():
        _exercise_firestore(collection)

    _test()


@background_task()
def test_firestore_query_generators(collection, assert_trace_for_generator):
    query = collection.select("x").where("x", "<=", 3)
    assert_trace_for_generator(query.stream)


@validate_database_duration()
@background_task()
def test_firestore_query_db_duration(collection):
    _exercise_firestore(collection)