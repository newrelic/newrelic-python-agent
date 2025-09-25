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

import json

import pytest
from autogen_core import FunctionCall
from autogen_core.models import CreateResult, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

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
    app_name="Python Agent Test (mlmodel_autogen)", default_settings=_default_settings
)


@pytest.fixture
def single_tool_model_client():
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"message": "Hello"}), name="add_exclamation")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            "Hello",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": "gpt-4.1-nano",
            "structured_output": True,
        },
    )
    return model_client


@pytest.fixture
def single_tool_model_client_error():
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                # Set arguments to an invalid type to trigger error in tool
                content=[FunctionCall(id="1", arguments=12, name="add_exclamation")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            "Hello",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": "gpt-4.1-nano",
            "structured_output": True,
        },
    )
    return model_client


@pytest.fixture
def multi_tool_model_client():
    model_client = ReplayChatCompletionClient(
        chat_completions=[
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", name="add_exclamation", arguments=json.dumps({"message": "Hello"}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="3", name="compute_sum", arguments=json.dumps({"a": 5, "b": 3}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="2", name="add_exclamation", arguments=json.dumps({"message": "Goodbye"}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="4", name="compute_sum", arguments=json.dumps({"a": 123, "b": 2}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ],
        model_info={
            "family": "gpt-4.1-nano",
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "structured_output": True,
        },
    )
    return model_client


@pytest.fixture
def multi_tool_model_client_error():
    model_client = ReplayChatCompletionClient(
        chat_completions=[
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", name="add_exclamation", arguments=json.dumps({"message": "Hello"}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="2", name="add_exclamation", arguments=json.dumps({"message": "Goodbye"}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="3", name="compute_sum", arguments=json.dumps({"a": 5, "b": 3}))],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            CreateResult(
                finish_reason="function_calls",
                # Set arguments to an invalid type to trigger error in tool
                content=[FunctionCall(id="4", name="compute_sum", arguments=12)],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ],
        model_info={
            "family": "gpt-4.1-nano",
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "structured_output": True,
        },
    )
    return model_client
