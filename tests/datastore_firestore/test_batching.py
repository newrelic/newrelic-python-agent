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

from testing_support.validators.validate_database_duration import (
    validate_database_duration,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

# ===== WriteBatch =====


def _exercise_write_batch(client, collection):
    docs = [collection.document(str(x)) for x in range(1, 4)]
    batch = client.batch()
    for doc in docs:
        batch.set(doc, {})

    batch.commit()


def test_firestore_write_batch(client, collection):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/commit", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_write_batch",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_write_batch")
    def _test():
        _exercise_write_batch(client, collection)

    _test()


# ===== BulkWriteBatch =====


def _exercise_bulk_write_batch(client, collection):
    from google.cloud.firestore_v1.bulk_batch import BulkWriteBatch

    docs = [collection.document(str(x)) for x in range(1, 4)]
    batch = BulkWriteBatch(client)
    for doc in docs:
        batch.set(doc, {})

    batch.commit()


def test_firestore_bulk_write_batch(client, collection):
    _test_scoped_metrics = [
        ("Datastore/operation/Firestore/commit", 1),
    ]

    _test_rollup_metrics = [
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_bulk_write_batch",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_bulk_write_batch")
    def _test():
        _exercise_bulk_write_batch(client, collection)

    _test()
