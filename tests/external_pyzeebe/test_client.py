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

import pytest
from newrelic.api.background_task import BackgroundTask
from newrelic.api.application import application_instance

async def test_run_process_outside_transaction(collector_agent_registration, pyzeebe, monkeypatch):
    channel = pyzeebe.create_insecure_channel("localhost:1")
    client = pyzeebe.ZeebeClient(channel)

    async def dummy_run_process(self, bpmn_process_id, *args, **kwargs):
        return 123

    monkeypatch.object(pyzeebe.client.client.ZeebeClient, "run_process", dummy_run_process, raising=False)
    result = await client.run_process("fake_process_id")
    assert result == 123

    recorded_txn = collector_agent_registration.recorded_transaction

    assert recorded_txn["name"] == "ZeebeClient/run_process"

    assert recorded_txn["type"] == "OtherTransaction/Background"

    root_segment = recorded_txn["trace_segment"]
    assert root_segment["name"] == "ZeebeClient/run_process"
    assert not root_segment["children"]


async def test_run_process_inside_transaction(collector_agent_registration, pyzeebe, monkeypatch):
    channel = pyzeebe.create_insecure_channel("localhost:1")
    client = pyzeebe.ZeebeClient(channel)

    async def dummy_run_process(self, bpmn_process_id, *args, **kwargs):
        return 456

    monkeypatch.object(pyzeebe.client.client.ZeebeClient, "run_process", dummy_run_process, raising=False)

    with BackgroundTask(application_instance(), name="TestSpan", group="ZeebeClient"):
        result = await client.run_process("dummy_process")
    assert result == 456

    recorded_txn = collector_agent_registration.recorded_transaction
    assert recorded_txn["name"] == "ZeebeClient/TestSpan"
    assert recorded_txn["type"] == "OtherTransaction/Background"    

    root_segment = recorded_txn["trace_segment"]
    assert any(seg["name"] == "ZeebeClient/run_process" for seg in root_segment["children"])

