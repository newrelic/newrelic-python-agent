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
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_with_context_attrs,
    set_trace_info,
    tool_events_sans_content,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version_tuple

AUTOGEN_VERSION = get_package_version_tuple("autogen-agentchat")

tool_recorded_event = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": "1",
            "output": "Hello!",
            "name": "add_exclamation",
            "agent_name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"message": "Hello"}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]

tool_recorded_event_error = [
    (
        {"type": "LlmTool"},
        {
            "id": None,
            "run_id": "1",
            "name": "add_exclamation",
            "agent_name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "12",
            "vendor": "autogen",
            "ingest_source": "Python",
            "error": True,
            "duration": None,
        },
    )
]


agent_recorded_event = [
    (
        {"type": "LlmAgent"},
        {
            "id": None,
            "name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]


# Example tool for testing purposes
def add_exclamation(message: str) -> str:
    return f"{message}!"


@reset_core_stats_engine()
@validate_custom_events(
    events_with_context_attrs(tool_recorded_event) + events_with_context_attrs(agent_recorded_event)
)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_assistant_agent:test_run_assistant_agent",
    scoped_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    rollup_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "pirate_agent"}'})
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@background_task()
def test_run_assistant_agent(loop, set_trace_info, single_tool_model_client):
    set_trace_info()
    pirate_agent = AssistantAgent(
        name="pirate_agent", model_client=single_tool_model_client, tools=[add_exclamation], model_client_stream=True
    )

    async def _test():
        with WithLlmCustomAttributes({"context": "attr"}):
            response = await pirate_agent.run()
        assert "Hello!" in response.messages[1].content[0].content

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@validate_custom_events(tool_recorded_event + agent_recorded_event)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_assistant_agent:test_run_stream_assistant_agent",
    scoped_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    rollup_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "pirate_agent"}'})
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@background_task()
def test_run_stream_assistant_agent(loop, set_trace_info, single_tool_model_client):
    set_trace_info()

    pirate_agent = AssistantAgent(
        name="pirate_agent", model_client=single_tool_model_client, tools=[add_exclamation], model_client_stream=True
    )

    async def _test():
        response = pirate_agent.run_stream()
        result = ""
        async for message in response:
            if not isinstance(message, TaskResult):
                result += message.to_text()
            else:
                break

        assert "Hello!" in result

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(tool_events_sans_content(tool_recorded_event) + agent_recorded_event)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_assistant_agent:test_run_assistant_agent_no_content",
    scoped_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    rollup_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "pirate_agent"}'})
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@background_task()
def test_run_assistant_agent_no_content(loop, set_trace_info, single_tool_model_client):
    set_trace_info()
    pirate_agent = AssistantAgent(
        name="pirate_agent", model_client=single_tool_model_client, tools=[add_exclamation], model_client_stream=True
    )

    async def _test():
        response = await pirate_agent.run()
        assert "Hello!" in response.messages[1].content[0].content

    loop.run_until_complete(_test())


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_run_assistant_agent_disabled_ai_monitoring_events(loop, set_trace_info, single_tool_model_client):
    set_trace_info()
    pirate_agent = AssistantAgent(
        name="pirate_agent", model_client=single_tool_model_client, tools=[add_exclamation], model_client_stream=True
    )

    async def _test():
        response = await pirate_agent.run()
        assert "Hello!" in response.messages[1].content[0].content

    loop.run_until_complete(_test())


SKIP_IF_AUTOGEN_062 = pytest.mark.skipif(
    AUTOGEN_VERSION > (0, 6, 1),
    reason="Forcing invalid tool call arguments causes a hang on autogen versions above 0.6.1",
)


@SKIP_IF_AUTOGEN_062
@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(tool_recorded_event_error)
@validate_custom_event_count(count=2)
@validate_transaction_metrics(
    "test_assistant_agent:test_run_assistant_agent_error",
    scoped_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    rollup_metrics=[
        (
            "Llm/agent/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent",
            1,
        ),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            1,
        ),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "pirate_agent"}'})
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_TOOL", "name": "add_exclamation"}'})
@background_task()
def test_run_assistant_agent_error(loop, set_trace_info, single_tool_model_client_error):
    set_trace_info()
    pirate_agent = AssistantAgent(
        name="pirate_agent",
        model_client=single_tool_model_client_error,
        tools=[add_exclamation],
        model_client_stream=False,
    )

    async def _test():
        with pytest.raises(TypeError):
            await pirate_agent.run()

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_run_assistant_agent_outside_txn(loop, single_tool_model_client):
    pirate_agent = AssistantAgent(
        name="pirate_agent", model_client=single_tool_model_client, tools=[add_exclamation], model_client_stream=True
    )

    async def _test():
        response = await pirate_agent.run()
        assert "Hello!" in response.messages[1].content[0].content

    loop.run_until_complete(_test())
