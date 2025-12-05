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

from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import disabled_ai_monitoring_settings, events_with_context_attrs
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes

from ._test_multiagent_graph import agent_graph, analysis_agent, analysis_model, math_agent, math_model

agent_recorded_events = [
    [
        {"type": "LlmAgent"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "name": "math_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "strands",
        },
    ],
    [
        {"type": "LlmAgent"},
        {
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "name": "analysis_agent",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "strands",
        },
    ],
]

tool_recorded_events = [
    [
        {"type": "LlmTool"},
        {
            "agent_name": "math_agent",
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "input": "{'a': 15, 'b': 27}",
            "name": "calculate_sum",
            "output": "{'text': '42'}",
            "run_id": "123",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "strands",
        },
    ],
    [
        {"type": "LlmTool"},
        {
            "agent_name": "analysis_agent",
            "duration": None,
            "id": None,
            "ingest_source": "Python",
            "input": "{'value': 42}",
            "name": "analyze_result",
            "output": "{'text': 'The result 42 is positive'}",
            "run_id": "456",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "strands",
        },
    ],
]


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(tool_recorded_events))
@validate_custom_events(events_with_context_attrs(agent_recorded_events))
@validate_custom_event_count(count=4)  # 2 LlmTool events, 2 LlmAgent events
@validate_transaction_metrics(
    "mlmodel_strands.test_multiagent_graph:test_multiagent_graph_invoke",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/math_agent", 1),
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/analysis_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/calculate_sum", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/analyze_result", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/math_agent", 1),
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/analysis_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/calculate_sum", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/analyze_result", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_multiagent_graph_invoke(set_trace_info, agent_graph):
    set_trace_info()

    with WithLlmCustomAttributes({"context": "attr"}):
        response = agent_graph("Calculate the sum of 15 and 27.")

    assert response.execution_count == 2
    assert not response.failed_nodes
    assert response.results["math"].result.message["content"][0]["text"] == "The sum of 15 and 27 is 42."
    assert (
        response.results["analysis"].result.message["content"][0]["text"]
        == "The calculation is correct, and 42 is a positive integer result."
    )


@reset_core_stats_engine()
@validate_custom_events(tool_recorded_events)
@validate_custom_events(agent_recorded_events)
@validate_custom_event_count(count=4)  # 2 LlmTool events, 2 LlmAgent events
@validate_transaction_metrics(
    "mlmodel_strands.test_multiagent_graph:test_multiagent_graph_invoke_async",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/math_agent", 1),
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/analysis_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/calculate_sum", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/analyze_result", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/math_agent", 1),
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/analysis_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/calculate_sum", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/analyze_result", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_multiagent_graph_invoke_async(loop, set_trace_info, agent_graph):
    set_trace_info()

    async def _test():
        response = await agent_graph.invoke_async("Calculate the sum of 15 and 27.")

        assert response.execution_count == 2
        assert not response.failed_nodes
        assert response.results["math"].result.message["content"][0]["text"] == "The sum of 15 and 27 is 42."
        assert (
            response.results["analysis"].result.message["content"][0]["text"]
            == "The calculation is correct, and 42 is a positive integer result."
        )

    loop.run_until_complete(_test())


@reset_core_stats_engine()
@validate_custom_events(tool_recorded_events)
@validate_custom_events(agent_recorded_events)
@validate_custom_event_count(count=4)  # 2 LlmTool events, 2 LlmAgent events
@validate_transaction_metrics(
    "mlmodel_strands.test_multiagent_graph:test_multiagent_graph_stream_async",
    scoped_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/math_agent", 1),
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/analysis_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/calculate_sum", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/analyze_result", 1),
    ],
    rollup_metrics=[
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/math_agent", 1),
        ("Llm/agent/Strands/strands.agent.agent:Agent.stream_async/analysis_agent", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/calculate_sum", 1),
        ("Llm/tool/Strands/strands.tools.executors._executor:ToolExecutor._stream/analyze_result", 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_multiagent_graph_stream_async(loop, set_trace_info, agent_graph):
    set_trace_info()

    async def _test():
        response = agent_graph.stream_async("Calculate the sum of 15 and 27.")
        messages = [
            event["node_result"].result.message async for event in response if event["type"] == "multiagent_node_stop"
        ]

        assert len(messages) == 2

        assert messages[0]["content"][0]["text"] == "The sum of 15 and 27 is 42."
        assert messages[1]["content"][0]["text"] == "The calculation is correct, and 42 is a positive integer result."

    loop.run_until_complete(_test())


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_multiagent_graph_invoke_disabled_ai_monitoring_events(set_trace_info, agent_graph):
    set_trace_info()

    response = agent_graph("Calculate the sum of 15 and 27.")

    assert response.execution_count == 2
    assert not response.failed_nodes
    assert response.results["math"].result.message["content"][0]["text"] == "The sum of 15 and 27 is 42."
    assert (
        response.results["analysis"].result.message["content"][0]["text"]
        == "The calculation is correct, and 42 is a positive integer result."
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_multiagent_graph_invoke_outside_txn(agent_graph):
    response = agent_graph("Calculate the sum of 15 and 27.")

    assert response.execution_count == 2
    assert not response.failed_nodes
    assert response.results["math"].result.message["content"][0]["text"] == "The sum of 15 and 27 is 42."
    assert (
        response.results["analysis"].result.message["content"][0]["text"]
        == "The calculation is correct, and 42 is a positive integer result."
    )
