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

from _target_application import add, assert_dt
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@validate_transaction_metrics(
    name="_target_application.assert_dt",
    group="Celery",
    rollup_metrics=[
        ("Supportability/DistributedTrace/AcceptPayload/Success", None),
        ("Supportability/TraceContext/Accept/Success", 1),
    ],
    background_task=True,
    index=-2,
)
@validate_transaction_metrics(
    name="test_distributed_tracing:test_celery_task_distributed_tracing_enabled", background_task=True
)
@validate_transaction_count(2)
@background_task()
def test_celery_task_distributed_tracing_enabled():
    result = assert_dt.apply_async()
    result = result.get()
    assert result == 1


@override_application_settings({"distributed_tracing.enabled": False})
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    rollup_metrics=[
        ("Supportability/DistributedTrace/AcceptPayload/Success", None),
        ("Supportability/TraceContext/Accept/Success", None),  # No trace context should be accepted
    ],
    background_task=True,
    index=-2,
)
@validate_transaction_metrics(
    name="test_distributed_tracing:test_celery_task_distributed_tracing_disabled", background_task=True
)
@validate_transaction_count(2)
@background_task()
def test_celery_task_distributed_tracing_disabled():
    result = add.apply_async((1, 2))
    result = result.get()
    assert result == 3
