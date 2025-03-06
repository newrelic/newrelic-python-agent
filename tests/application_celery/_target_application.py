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

from celery import Celery, shared_task
from testing_support.validators.validate_distributed_trace_accepted import validate_distributed_trace_accepted

from newrelic.api.transaction import current_transaction

app = Celery(
    "tasks",
    broker_url="memory://",
    result_backend="cache+memory://",
    worker_hijack_root_logger=False,
    pool="solo",
    broker_heartbeat=0,
)


@app.task
def add(x, y):
    return x + y


@app.task
def tsum(nums):
    return sum(nums)


@app.task
def nested_add(x, y):
    return add(x, y)


@shared_task
def shared_task_add(x, y):
    return x + y


@app.task
@validate_distributed_trace_accepted(transport_type="AMQP")
def assert_dt():
    # Basic checks for DT delegated to task
    txn = current_transaction()
    assert txn, "No transaction active."
    assert txn.name == "_target_application.assert_dt", f"Transaction name does not match: {txn.name}"
    return 1
