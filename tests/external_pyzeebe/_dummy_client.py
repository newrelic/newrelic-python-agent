class DummyProcessResult:
    def __init__(self, key: int):
        self.process_instance_key = key

class ZeebeClient:
    async def run_process(self, *args, **kwargs):
        return DummyProcessResult(key=12345)

    async def run_process_with_result(self, *args, **kwargs):
        return DummyProcessResult(key=12345)
    
    async def deploy_resource(self, *args, **kwargs):
        return {"deployment_key": 33333, "resources": list(args)}

    async def publish_message(self, name: str, correlation_key: str, variables: dict = None):
        return {"message_key": 56789}
    

