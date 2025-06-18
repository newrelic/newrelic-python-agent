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

import asyncio

from _mocks import DummyZeebeAdapter
from pyzeebe import Job, JobStatus, ZeebeTaskRouter
from pyzeebe.worker.job_executor import JobController, JobExecutor
from pyzeebe.worker.task_state import TaskState
from testing_support.validators.validate_custom_parameters import validate_custom_parameters
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

# Set up a router with a dummy async task
router = ZeebeTaskRouter()


@router.task(task_type="testTask")
async def dummy_task(x: int) -> dict:
    """
    Simulate a task function that reads input variable x
    """
    return {"result": x}


@validate_transaction_metrics(name="test_process/testTask", group="ZeebeTask", scoped_metrics=[], background_task=True)
@validate_custom_parameters(
    required_params=[
        ("zeebe.job.key", 123),
        ("zeebe.job.type", "testTask"),
        ("zeebe.job.bpmnProcessId", "test_process"),
        ("zeebe.job.processInstanceKey", 456),
        ("zeebe.job.elementId", "service_task_123"),
    ]
)
def test_execute_one_job(loop):
    dummy_adapter = DummyZeebeAdapter()

    # Build a Job with fixed values
    job = Job(
        key=123,
        type="testTask",  # must match router.task(task_type="testTask")
        bpmn_process_id="test_process",
        process_instance_key=456,
        process_definition_version=1,
        process_definition_key=789,
        element_id="service_task_123",
        element_instance_key=321,
        custom_headers={},
        worker="test_worker",
        retries=3,
        deadline=0,
        variables={"x": 33},
        status=JobStatus.Running,
    )

    # JobExecutor constructor params init
    task_obj = router.get_task("testTask")
    assert task_obj is not None
    jobs_queue = asyncio.Queue()
    task_state = TaskState()

    job_executor = JobExecutor(task_obj, jobs_queue, task_state, dummy_adapter)

    # Build a JobController for completion logic.
    job_controller = JobController(job, dummy_adapter)

    loop.run_until_complete(job_executor.execute_one_job(job, job_controller))
    assert job.variables["x"] == 33
