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
import asyncio
import sys, types
import _dummy_client as dummy_client

from newrelic.api.background_task import background_task

# Force import system to use dummy ZeebeClient
pyzeebe_mod = types.ModuleType("pyzeebe")
pyzeebe_client_pkg = types.ModuleType("pyzeebe.client")

pyzeebe_mod.client = pyzeebe_client_pkg
pyzeebe_client_pkg.client = dummy_client

sys.modules["pyzeebe"] = pyzeebe_mod
sys.modules["pyzeebe.client"] = pyzeebe_client_pkg
sys.modules["pyzeebe.client.client"] = dummy_client

from pyzeebe.client.client import ZeebeClient
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

@validate_transaction_metrics(
    "test_client_methods:function_trace",
    rollup_metrics=[
        ("ZeebeClient/run_process", 1),
        ("ZeebeClient/run_process_with_result", 1),
        ("ZeebeClient/deploy_resource", 1),
        ("ZeebeClient/publish_message", 1)
    ],
    background_task=True,
)
def test_client_methods_as_function_traces():
    @background_task(name="test_client_methods:function_trace")
    def _test():
        client = ZeebeClient()
        
        #run_process
        result_1 = asyncio.run(client.run_process("DummyProcess"))
        assert hasattr(result_1, "process_instance_key")
        assert result_1.process_instance_key == 12345

        #run_process_with_result
        result_2 = asyncio.run(client.run_process_with_result("DummyProcess"))
        assert hasattr(result_2, "process_instance_key")
        assert result_2.process_instance_key == 45678

        # deploy_resource
        result_3 = asyncio.run(client.deploy_resource("test-workflow.bpmn"))
        assert result_3["deployment_key"] == 33333

        # publish_message
        result_4 = asyncio.run(client.publish_message("test_message"))
        assert result_4["message_key"] == 56789
    _test()


# # TODO: fix failure
# @validate_transaction_metrics(
#     "ZeebeClient/run_process",
#     rollup_metrics=[
#         ("OtherTransaction/ZeebeClient/run_process", 1),
#     ],
#     background_task=True,
# )
# def test_run_process_as_background_tx():
#     client = ZeebeClient()
#     result = asyncio.run(client.run_process("DummyProcess"))
#     assert hasattr(result, "process_instance_key")
#     assert result.process_instance_key == 12345