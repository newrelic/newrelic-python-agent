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

from _target_application import add, assert_dt
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

from newrelic.packages import six

skip_if_py2 = pytest.mark.skipif(
    six.PY2, reason="Celery has no pytest plugin for Python 2, making testing very difficult."
)


@pytest.fixture(scope="module")
def celery_config():
    # Used by celery pytest plugin to configure Celery instance
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
    }


@pytest.fixture(scope="module")
def celery_worker_parameters():
    # Used by celery pytest plugin to configure worker instance
    return {"shutdown_timeout": 120}


@skip_if_py2
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
    name="test_celery_distributed_tracing:test_celery_task_distributed_tracing",
    background_task=True,
)
@validate_transaction_count(2)
@background_task()
def test_celery_task_distributed_tracing(celery_worker):
    result = assert_dt.apply_async()
    while not result.ready():
        pass
    result = result.result
    assert result == 1


@skip_if_py2
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
    name="test_celery_distributed_tracing:test_celery_task_distributed_tracing_disabled",
    background_task=True,
)
@validate_transaction_count(2)
@background_task()
def test_celery_task_distributed_tracing_disabled(celery_worker):
    result = add.apply_async((1, 2))
    while not result.ready():
        pass
    result = result.result
    assert result == 3
