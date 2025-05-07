from pyzeebe import ZeebeClient

class DummyZeebeClient(ZeebeClient):
    def __init__(self, *args, **kwargs):
        pass

    async def run_process(self, process_id: str, *args, **kwargs):
        return None
    
def create_dummy_client():
    return DummyZeebeClient()

