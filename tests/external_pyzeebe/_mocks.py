from types import SimpleNamespace
from pyzeebe.grpc_internals.zeebe_adapter import ZeebeAdapter

# Dummy response objects with only required fields
DummyCreateProcessInstanceResponse = SimpleNamespace(process_instance_key=12345)

DummyCreateProcessInstanceWithResultResponse = SimpleNamespace(
    process_instance_key=45678, variables={"result": "success"}
)

DummyDeployResourceResponse = SimpleNamespace(key=67890, deployments=[], tenant_id=None)

DummyPublishMessageResponse = SimpleNamespace(key=99999, tenant_id=None)


# Dummy RPC stub coroutines
async def dummy_create_process_instance(
    self, bpmn_process_id: str, variables: dict = None, version: int = -1, tenant_id: str = None
):
    """Simulate ZeebeAdapter.create_process_instance"""
    return DummyCreateProcessInstanceResponse


async def dummy_create_process_instance_with_result(
    self,
    bpmn_process_id: str,
    variables: dict = None,
    version: int = -1,
    timeout: int = 0,
    variables_to_fetch=None,
    tenant_id: str = None,
):
    """Simulate ZeebeAdapter.create_process_instance_with_result"""
    return DummyCreateProcessInstanceWithResultResponse


async def dummy_deploy_resource(*resource_file_path: str, tenant_id: str = None):
    """Simulate ZeebeAdapter.deploy_resource"""
    # Create dummy deployment metadata for each provided resource path
    deployments = []
    for path in resource_file_path:
        deployments.append(
            SimpleNamespace(
                resource_name=str(path),
                bpmn_process_id="dummy_process",
                process_definition_key=123,
                version=1,
                tenant_id=tenant_id if tenant_id is not None else None,
            )
        )
    # Create a dummy response with a list of deployments
    return SimpleNamespace(
        deployment_key=333333, deployments=deployments, tenant_id=tenant_id if tenant_id is not None else None
    )


async def dummy_publish_message(
    self,
    name: str,
    correlation_key: str,
    variables: dict = None,
    time_to_live_in_milliseconds: int = 60000,
    message_id: str = None,
    tenant_id: str = None,
):
    """Simulate ZeebeAdapter.publish_message"""
    # Return the dummy response (contains message key)
    return SimpleNamespace(key=999999, tenant_id=tenant_id if tenant_id is not None else None)


async def dummy_complete_job(self, job_key: int, variables: dict):
    """Simulate JobExecutor.complete_job"""
    setattr(self, "_last_complete", {"job_key": job_key, "variables": variables})
    return None


class DummyZeebeAdapter(ZeebeAdapter):
    """Simulate a ZeebeAdapter so JobExecutor can be instatiated w/o gRPC channel"""

    def __init__(self):
        self.completed_job_key = None
        self.completed_job_vars = None

    async def complete_job(self, job_key: int, variables: dict):
        self.completed_job_key = job_key
        self.completed_job_vars = variables
        return None
