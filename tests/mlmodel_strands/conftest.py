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
from _mock_model_provider import MockedModelProvider
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.ml_testing_utils import set_trace_info

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slowdowns.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_strands)", default_settings=_default_settings
)


@pytest.fixture
def single_tool_model():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "Hello"}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model


@pytest.fixture
def single_tool_model_runtime_error_coro():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling throw_exception_coro tool"},
                    # Set arguments to an invalid type to trigger error in tool
                    {"toolUse": {"name": "throw_exception_coro", "toolUseId": "123", "input": {"message": "Hello"}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model


@pytest.fixture
def single_tool_model_runtime_error_agen():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling throw_exception_agen tool"},
                    # Set arguments to an invalid type to trigger error in tool
                    {"toolUse": {"name": "throw_exception_agen", "toolUseId": "123", "input": {"message": "Hello"}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model


@pytest.fixture
def multi_tool_model():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "Hello"}}},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling compute_sum tool"},
                    {"toolUse": {"name": "compute_sum", "toolUseId": "123", "input": {"a": 5, "b": 3}}},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "Goodbye"}}},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling compute_sum tool"},
                    {"toolUse": {"name": "compute_sum", "toolUseId": "123", "input": {"a": 123, "b": 2}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model


@pytest.fixture
def multi_tool_model_error():
    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "Hello"}}},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling compute_sum tool"},
                    {"toolUse": {"name": "compute_sum", "toolUseId": "123", "input": {"a": 5, "b": 3}}},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling add_exclamation tool"},
                    {"toolUse": {"name": "add_exclamation", "toolUseId": "123", "input": {"message": "Goodbye"}}},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Calling compute_sum tool"},
                    # Set insufficient arguments to trigger error in tool
                    {"toolUse": {"name": "compute_sum", "toolUseId": "123", "input": {"a": 123}}},
                ],
            },
            {"role": "assistant", "content": [{"text": "Success!"}]},
        ]
    )
    return model
