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
from _target_application import add
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.mark.parametrize("dt_enabled", [True, False])
def test_celery_task_distributed_tracing_inside_background_task(dt_enabled):
    @override_application_settings({"distributed_tracing.enabled": dt_enabled})
    @validate_transaction_metrics(
        name="_target_application.add",
        group="Celery",
        rollup_metrics=[
            ("Supportability/TraceContext/Accept/Success", 1 if dt_enabled else None),
            ("Supportability/TraceContext/TraceParent/Accept/Success", 1 if dt_enabled else None),
        ],
        background_task=True,
        index=-2,
    )
    @validate_transaction_metrics(
        name="test_distributed_tracing:test_celery_task_distributed_tracing_inside_background_task.<locals>._test",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1 if dt_enabled else None),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1 if dt_enabled else None),
        ],
        background_task=True,
    )
    @validate_transaction_count(2)  # One for the background task, one for the Celery task.  Runs in different processes.
    @background_task()
    def _test():
        result = add.apply_async((1, 2))
        result = result.get()
        assert result == 3

    _test()
    
    
@pytest.mark.parametrize("dt_enabled", [True, False])
def test_celery_task_distributed_tracing_outside_background_task(dt_enabled):
    @override_application_settings({"distributed_tracing.enabled": dt_enabled})
    @validate_transaction_metrics(
        name="_target_application.add",
        group="Celery",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1 if dt_enabled else None),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1 if dt_enabled else None),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)
    def _test():
        result = add.apply_async((1, 2))
        result = result.get()
        assert result == 3

    _test()
    

# In this case, the background task creating the transaction 
# has not generated a distributed trace header, so the Celery 
# task will not have a distributed trace header to accept.
@pytest.mark.parametrize("dt_enabled", [True, False])
def test_celery_task_distributed_tracing_inside_background_task_apply(dt_enabled):
    @override_application_settings({"distributed_tracing.enabled": dt_enabled})
    @validate_transaction_metrics(
        name="test_distributed_tracing:test_celery_task_distributed_tracing_inside_background_task_apply.<locals>._test",
        background_task=True,
    )
    @validate_transaction_count(1)  # In the same process, so only one transaction
    @background_task()
    def _test():
        result = add.apply((1, 2))
        result = result.get()
        assert result == 3

    _test()
    
    
@pytest.mark.parametrize("dt_enabled", [True, False])
def test_celery_task_distributed_tracing_outside_background_task_apply(dt_enabled):
    @override_application_settings({"distributed_tracing.enabled": dt_enabled})
    @validate_transaction_metrics(
        name="_target_application.add",
        group="Celery",
        rollup_metrics=[
            ("Supportability/TraceContext/Create/Success", 1 if dt_enabled else None),
            ("Supportability/DistributedTrace/CreatePayload/Success", 1 if dt_enabled else None),
        ],
        background_task=True,
    )
    @validate_transaction_count(1)  # In the same process, so only one transaction
    def _test():
        result = add.apply((1, 2))
        result = result.get()
        assert result == 3

    _test()