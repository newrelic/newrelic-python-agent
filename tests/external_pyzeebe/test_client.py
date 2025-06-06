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
from pyzeebe import ZeebeClient, create_insecure_channel
from pyzeebe.grpc_internals.zeebe_adapter import ZeebeAdapter
from _mocks import dummy_create_process_instance, dummy_create_process_instance_with_result, dummy_deploy_resource, dummy_publish_message

from newrelic.api.background_task import background_task
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.fixtures import validate_attributes


client = ZeebeClient(create_insecure_channel())

@validate_transaction_metrics(
    "test_zeebe_client:run_process",
    rollup_metrics=[
        ("ZeebeClient/run_process", 1)
    ],
    background_task=True
)
@validate_attributes("agent", ["zeebe.client.bpmnProcessId"])
def test_run_process(monkeypatch):
    monkeypatch.setattr(ZeebeAdapter, "create_process_instance", dummy_create_process_instance)

    @background_task(name="test_zeebe_client:run_process")
    def _test():
        response = asyncio.run(client.run_process("test_process"))
        assert response.process_instance_key == 12345
    _test()


@validate_transaction_metrics(
    "test_zeebe_client:run_process_with_result",
    rollup_metrics=[
        ("ZeebeClient/run_process_with_result", 1)
    ],
    background_task=True
)
@validate_attributes("agent", ["zeebe.client.bpmnProcessId"])
def test_run_process_with_result(monkeypatch):
    monkeypatch.setattr(ZeebeAdapter, "create_process_instance_with_result", dummy_create_process_instance_with_result)

    @background_task(name="test_zeebe_client:run_process_with_result")
    def _test():
        result = asyncio.run(client.run_process_with_result("test_process"))
        assert result.process_instance_key == 45678
        assert result.variables == {"result": "success"}
    _test()


@validate_transaction_metrics(
    "test_zeebe_client:deploy_resource",
    rollup_metrics=[
        ("ZeebeClient/deploy_resource", 1)
    ],
    background_task=True
)
@validate_attributes("agent", ["zeebe.client.resourceCount", "zeebe.client.resourceFile"])
def test_deploy_resource(monkeypatch):
    monkeypatch.setattr(ZeebeAdapter, "deploy_resource", dummy_deploy_resource)

    @background_task(name="test_zeebe_client:deploy_resource")
    def _test():
        result = asyncio.run(client.deploy_resource("test.bpmn"))
        assert result.deployment_key == 333333
    _test()


@validate_transaction_metrics(
    "test_zeebe_client:publish_message",
    rollup_metrics=[
        ("ZeebeClient/publish_message", 1)
    ],
    background_task=True
)
@validate_attributes("agent", ["zeebe.client.messageName", "zeebe.client.correlationKey", "zeebe.client.messageId"])
def test_publish_message(monkeypatch):
    monkeypatch.setattr(ZeebeAdapter, "publish_message", dummy_publish_message)

    @background_task(name="test_zeebe_client:publish_message")
    def _test():
        result = asyncio.run(client.publish_message(name="test_message", correlation_key="999999", message_id="abc123"))
        assert result.key == 999999
    _test()