import asyncio
import pytest

from pyzeebe import Job, ZeebeTaskRouter, JobStatus
from pyzeebe.worker.job_executor import JobExecutor, JobController
from pyzeebe.worker.task_state import TaskState
from _mocks import DummyZeebeAdapter

# from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_custom_parameters import validate_custom_parameters

# Set up a router with a dummy async task
router = ZeebeTaskRouter()

@router.task(task_type="testTask")
async def dummy_task(x: int) -> dict:
    """
    Simulate a task function that reads input variable 'x'
    and adds 1.
    """
    return {"result": x }

# @validate_transaction_metrics(
#     "ZeebeTask/test_process/testTask",
#     rollup_metrics=[
#         ("ZeebeTask/test_process/testTask", 1)
#     ],
#     background_task=True
# )
@validate_custom_parameters(required_params=[
    ("zeebe.job.key", 123),
    ("zeebe.job.type", "testTask"),
    ("zeebe.job.bpmnProcessId", "test_process"),
    ("zeebe.job.processInstanceKey", 456),
    ("zeebe.job.elementId", "service_task_123")
])
def test_execute_one_job():
    dummy_adapter = DummyZeebeAdapter()

    # Build a Job with fixed values
    job = Job(
        key=123,
        type="testTask", # must match router.task(task_type="testTask")
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
        status=JobStatus.Running
    )

    # JobExecutor constructor params init
    task_obj = router.get_task("testTask")
    assert task_obj is not None
    jobs_queue = asyncio.Queue()
    task_state = TaskState()

    job_executor = JobExecutor(task_obj, jobs_queue, task_state, dummy_adapter)

    # Build a JobController for completion logic.
    job_controller = JobController(job, dummy_adapter)

    asyncio.run(job_executor.execute_one_job(job, job_controller))
    assert job.variables["x"] == 33