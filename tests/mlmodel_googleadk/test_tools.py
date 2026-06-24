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

from _test_agent import AGENT_NAME, PROMPT, agent_recorded_event, build_agent
from _test_tools import TOOL_NAME, get_capital_tool, tool_recorded_event
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_with_context_attrs,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.hooks.mlmodel_googleadk import GOOGLEADK_VERSION

EXPECTED_AGENT_METRIC = (f"Llm/agent/GoogleADK/run_async/{AGENT_NAME}", 1)
EXPECTED_TOOL_METRIC = (f"Llm/tool/GoogleADK/execute_single_function_call_async/{TOOL_NAME}", 1)
EXPECTED_SUPPORTABILITY_METRIC = (f"Supportability/Python/ML/GoogleADK/{GOOGLEADK_VERSION}", 1)


def _validate_events(events):
    assert len(events) == 3
    assert events[0].content.parts[0].function_call.name == "get_capital"
    assert events[1].content.parts[0].function_response.response["output"] == "Paris"
    assert events[2].content.parts[0].text == "Paris"


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(agent_recorded_event + tool_recorded_event(record_content=True)))
@validate_custom_event_count(count=8)  # LlmAgent, LlmTool, 2x (Summary, Input, Output) for the two LLM calls.
@validate_transaction_metrics(
    "test_tools:test_tool",
    scoped_metrics=[EXPECTED_AGENT_METRIC, EXPECTED_TOOL_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC, EXPECTED_TOOL_METRIC],
    custom_metrics=[EXPECTED_SUPPORTABILITY_METRIC],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
@validate_span_events(count=1, exact_agents={"subcomponent": f'{{"type": "APM-AI_TOOL", "name": "{TOOL_NAME}"}}'})
@background_task()
def test_tool(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent(tools=[get_capital_tool])
    with WithLlmCustomAttributes({"context": "attr"}):
        events = exercise_agent(agent, PROMPT)

    _validate_events(events)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(agent_recorded_event + tool_recorded_event(record_content=False))
@validate_custom_event_count(count=8)  # LlmAgent, LlmTool, 2x (Summary, Input, Output) for the two LLM calls.
@validate_transaction_metrics(
    "test_tools:test_tool_no_content",
    scoped_metrics=[EXPECTED_AGENT_METRIC, EXPECTED_TOOL_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC, EXPECTED_TOOL_METRIC],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_tool_no_content(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent(tools=[get_capital_tool])
    events = exercise_agent(agent, PROMPT)

    _validate_events(events)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_tools:test_tool_disabled_ai_monitoring", background_task=True)
@background_task()
def test_tool_disabled_ai_monitoring(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent(tools=[get_capital_tool])
    events = exercise_agent(agent, PROMPT)

    _validate_events(events)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_tool_outside_transaction(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent(tools=[get_capital_tool])
    events = exercise_agent(agent, PROMPT)

    _validate_events(events)
