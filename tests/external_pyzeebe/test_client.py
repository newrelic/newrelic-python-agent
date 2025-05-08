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
import _dummy_client as dummy_module

from newrelic.api.background_task import background_task

# Force import system to use dummy PyzeebeClient
pyzeebe_mod = types.ModuleType("pyzeebe")
pyzeebe_client_pkg = types.ModuleType("pyzeebe.client")

pyzeebe_mod.client = pyzeebe_client_pkg
pyzeebe_client_pkg.client = dummy_module

sys.modules["pyzeebe"] = pyzeebe_mod
sys.modules["pyzeebe.client"] = pyzeebe_client_pkg
sys.modules["pyzeebe.client.client"] = dummy_module

from pyzeebe.client.client import ZeebeClient
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

@validate_transaction_metrics(
    "test_run_process:function_trace",
    rollup_metrics=[("ZeebeClient/run_process", 1)],
    background_task=True,
)
def test_run_process_as_function_trace():
    @background_task(name="test_run_process:function_trace")
    def _test():
        client = ZeebeClient()
        result = asyncio.run(client.run_process("DummyProcess"))
        assert hasattr(result, "process_instance_key")
        assert result.process_instance_key == 12345
    _test()


# TODO: fix failure
@validate_transaction_metrics(
    "ZeebeClient/run_process",
    rollup_metrics=[
        ("OtherTransaction/ZeebeClient/run_process", 1),
    ],
    background_task=True,
)
def test_run_process_as_background_tx():
    client = ZeebeClient()
    result = asyncio.run(client.run_process("DummyProcess"))
    assert hasattr(result, "process_instance_key")
    assert result.process_instance_key == 12345