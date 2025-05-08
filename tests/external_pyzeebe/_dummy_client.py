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

class DummyProcessResult:
    def __init__(self, key: int):
        self.process_instance_key = key

class ZeebeClient:
    async def run_process(self, *args, **kwargs):
        return DummyProcessResult(key=12345)

    async def run_process_with_result(self, *args, **kwargs):
        return DummyProcessResult(key=45678)
    
    async def deploy_resource(self, *args, **kwargs):
        return {"deployment_key": 33333}

    async def publish_message(self, name: str, correlation_key: str = "", variables: dict = None):
        return {"message_key": 56789}
    

