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

from _mocks import (
    dummy_create_process_instance,
    dummy_create_process_instance_with_result,
    dummy_deploy_resource,
    dummy_publish_message,
)
from pyzeebe import ZeebeClient, create_insecure_channel
from pyzeebe.grpc_internals.zeebe_adapter import ZeebeAdapter
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

client = ZeebeClient(create_insecure_channel())


@validate_transaction_metrics(
    "test_zeebe_client:run_process", rollup_metrics=[("ZeebeClient/run_process", 1)], background_task=True
)
@validate_span_events(exact_agents={"zeebe.client.bpmnProcessId": "test_process"}, count=1)
def test_run_process(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "create_process_instance", dummy_create_process_instance)

    @background_task(name="test_zeebe_client:run_process")
    async def _test():
        response = await client.run_process("test_process")
        assert response.process_instance_key == 12345

    loop.run_until_complete(_test())


@validate_custom_event_count(count=0)
def test_run_process_outside_txn(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "create_process_instance", dummy_create_process_instance)

    async def _test():
        response = await client.run_process("test_process")
        assert response.process_instance_key == 12345

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_zeebe_client:run_process_with_result",
    rollup_metrics=[("ZeebeClient/run_process_with_result", 1)],
    background_task=True,
)
@validate_span_events(exact_agents={"zeebe.client.bpmnProcessId": "test_process"}, count=1)
def test_run_process_with_result(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "create_process_instance_with_result", dummy_create_process_instance_with_result)

    @background_task(name="test_zeebe_client:run_process_with_result")
    async def _test():
        result = await client.run_process_with_result("test_process")
        assert result.process_instance_key == 45678
        assert result.variables == {"result": "success"}

    loop.run_until_complete(_test())


@validate_custom_event_count(count=0)
def test_run_process_with_result_outside_txn(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "create_process_instance_with_result", dummy_create_process_instance_with_result)

    async def _test():
        result = await client.run_process_with_result("test_process")
        assert result.process_instance_key == 45678
        assert result.variables == {"result": "success"}

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_zeebe_client:deploy_resource", rollup_metrics=[("ZeebeClient/deploy_resource", 1)], background_task=True
)
@validate_span_events(exact_agents={"zeebe.client.resourceCount": 1, "zeebe.client.resourceFile": "test.bpmn"}, count=1)
def test_deploy_resource(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "deploy_resource", dummy_deploy_resource)

    @background_task(name="test_zeebe_client:deploy_resource")
    async def _test():
        result = await client.deploy_resource("test.bpmn")
        assert result.deployment_key == 333333

    loop.run_until_complete(_test())


@validate_custom_event_count(count=0)
def test_deploy_resource_outside_txn(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "deploy_resource", dummy_deploy_resource)

    async def _test():
        result = await client.deploy_resource("test.bpmn")
        assert result.deployment_key == 333333

    loop.run_until_complete(_test())


@validate_transaction_metrics(
    "test_zeebe_client:publish_message", rollup_metrics=[("ZeebeClient/publish_message", 1)], background_task=True
)
@validate_span_events(
    exact_agents={
        "zeebe.client.messageName": "test_message",
        "zeebe.client.correlationKey": "999999",
        "zeebe.client.messageId": "abc123",
    },
    count=1,
)
def test_publish_message(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "publish_message", dummy_publish_message)

    @background_task(name="test_zeebe_client:publish_message")
    async def _test():
        result = await client.publish_message(name="test_message", correlation_key="999999", message_id="abc123")
        assert result.key == 999999

    loop.run_until_complete(_test())


@validate_custom_event_count(count=0)
def test_publish_message_outside_txn(monkeypatch, loop):
    monkeypatch.setattr(ZeebeAdapter, "publish_message", dummy_publish_message)

    async def _test():
        result = await client.publish_message(name="test_message", correlation_key="999999", message_id="abc123")
        assert result.key == 999999

    loop.run_until_complete(_test())
