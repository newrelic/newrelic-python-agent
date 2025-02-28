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
def exercise_async_write_batch(async_client, async_collection):
    async def _exercise_async_write_batch():
        docs = [async_collection.document(str(x)) for x in range(1, 4)]
        async_batch = async_client.batch()
        for doc in docs:
            async_batch.set(doc, {})

        await async_batch.commit()

    return _exercise_async_write_batch


def test_firestore_async_write_batch(loop, exercise_async_write_batch, instance_info):
    _test_scoped_metrics = [("Datastore/operation/Firestore/commit", 1)]

    _test_rollup_metrics = [
        ("Datastore/all", 1),
        ("Datastore/allOther", 1),
        (f"Datastore/instance/Firestore/{instance_info['host']}/{instance_info['port_path_or_id']}", 1),
    ]

    @validate_database_duration()
    @validate_transaction_metrics(
        "test_firestore_async_write_batch",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_firestore_async_write_batch")
    def _test():
        loop.run_until_complete(exercise_async_write_batch())

    _test()


def test_firestore_async_write_batch_trace_node_datastore_params(loop, exercise_async_write_batch, instance_info):
    @validate_tt_collector_json(datastore_params=instance_info)
    @background_task()
    def _test():
        loop.run_until_complete(exercise_async_write_batch())

    _test()
