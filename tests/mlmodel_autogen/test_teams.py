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

import copy
import pytest
import logging

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.teams import RoundRobinGroupChat

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.common.object_names import callable_name


from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_with_context_attrs,
    set_trace_info,
    tool_events_sans_content,
)
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


team_tools_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "1",
            "output": "Hello!",
            "name": "add_exclamation",
            "agent_name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"input": "Hello"}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "2",
            "output": "Goodbye!",
            "name": "add_exclamation",
            "agent_name": "robot_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"input": "Goodbye"}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "3",
            "output": "8",
            "name": "compute_sum",
            "agent_name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"a": 5, "b": 3}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "4",
            "output": "125",
            "name": "compute_sum",
            "agent_name": "robot_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"a": 123, "b": 2}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
]

team_tools_recorded_events_error = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "1",
            "output": "Hello!",
            "name": "add_exclamation",
            "agent_name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"input": "Hello"}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "2",
            "output": "Goodbye!",
            "name": "add_exclamation",
            "agent_name": "robot_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"input": "Goodbye"}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "3",
            "output": "8",
            "name": "compute_sum",
            "agent_name": "pirate_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": '{"a": 5, "b": 3}',
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
        },
    ),
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": "4",
            "name": "compute_sum",
            "agent_name": "robot_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "12",
            "vendor": "autogen",
            "ingest_source": "Python",
            "duration": None,
            "error": True,
        },
    ),
]


# Example tool functions
def add_exclamation(input: str) -> str:
    return f"{input}!"


def compute_sum(a: int, b: int) -> int:
    return a + b


@reset_core_stats_engine()
@validate_custom_events(team_tools_recorded_events)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_teams:test_run_stream_round_robin_group",
    # Expect two of each metric since there are two agents executing two different tools each across 4 turns
    scoped_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent", 2),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            2,
        ),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    rollup_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/robot_agent", 2),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_run_stream_round_robin_group(loop, set_trace_info, multi_tool_model_client):
    set_trace_info()

    pirate_agent = AssistantAgent(
        name="pirate_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    robot_agent = AssistantAgent(
        name="robot_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    agents = RoundRobinGroupChat(participants=[pirate_agent, robot_agent], max_turns=4)

    async def _test():
        response = agents.run_stream()
        result = ""
        async for message in response:
            if not isinstance(message, TaskResult):
                result += message.to_text()
            else:
                break

        assert "Hello!" in result
        assert "Goodbye!" in result
        assert "8" in result
        assert "125" in result

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(team_tools_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_teams:test_run_round_robin_group",
    scoped_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent", 2),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            2,
        ),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    rollup_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/robot_agent", 2),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_run_round_robin_group(loop, set_trace_info, multi_tool_model_client):
    set_trace_info()

    pirate_agent = AssistantAgent(
        name="pirate_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    robot_agent = AssistantAgent(
        name="robot_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    agents = RoundRobinGroupChat(participants=[pirate_agent, robot_agent], max_turns=4)

    async def _test():
        with WithLlmCustomAttributes({"context": "attr"}):
            response = await agents.run()

        assert "Hello!" in response.messages[2].content
        assert "Goodbye!" in response.messages[5].content
        assert "8" in response.messages[8].content
        assert "125" in response.messages[11].content

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(tool_events_sans_content(team_tools_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_teams:test_run_round_robin_group_no_content",
    scoped_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent", 2),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            2,
        ),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    rollup_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/robot_agent", 2),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_run_round_robin_group_no_content(loop, set_trace_info, multi_tool_model_client):
    set_trace_info()

    pirate_agent = AssistantAgent(
        name="pirate_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    robot_agent = AssistantAgent(
        name="robot_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    agents = RoundRobinGroupChat(participants=[pirate_agent, robot_agent], max_turns=4)

    async def _test():
        response = await agents.run()
        assert "Hello!" in response.messages[1].content[0].content

    loop.run_until_complete(_test())


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_run_round_robin_group_disabled_ai_events(loop, set_trace_info, multi_tool_model_client):
    set_trace_info()

    pirate_agent = AssistantAgent(
        name="pirate_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    robot_agent = AssistantAgent(
        name="robot_agent",
        model_client=multi_tool_model_client,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    agents = RoundRobinGroupChat(participants=[pirate_agent, robot_agent], max_turns=4)

    async def _test():
        response = await agents.run()
        assert "Hello!" in response.messages[1].content[0].content

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_custom_events(team_tools_recorded_events_error)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_teams:test_run_round_robin_group_error",
    scoped_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/pirate_agent", 2),
        (
            "Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/add_exclamation",
            2,
        ),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    rollup_metrics=[
        ("Llm/autogen_agentchat.agents._assistant_agent:AssistantAgent.on_messages_stream/robot_agent", 2),
        ("Llm/tool/Autogen/autogen_agentchat.agents._assistant_agent:AssistantAgent._execute_tool_call/compute_sum", 2),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_run_round_robin_group_error(loop, set_trace_info, multi_tool_model_client_error):
    set_trace_info()

    pirate_agent = AssistantAgent(
        name="pirate_agent",
        model_client=multi_tool_model_client_error,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    robot_agent = AssistantAgent(
        name="robot_agent",
        model_client=multi_tool_model_client_error,
        tools=[add_exclamation, compute_sum],
        model_client_stream=True,
    )

    agents = RoundRobinGroupChat(participants=[pirate_agent, robot_agent], max_turns=4)

    async def _test():
        # run() should result in a RuntimeError wrapping a TypeError
        # Due to the async execution, the RuntimeError is what is raised despite the TypeError being the root cause
        with pytest.raises(RuntimeError):
            response = await agents.run()

    loop.run_until_complete(_test())
