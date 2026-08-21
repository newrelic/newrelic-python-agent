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

from _test_tools import TOOL_NAME, get_capital, tool_recorded_event
from conftest import EXPECTED_VERSION_METRICS, TOOL_PROMPT
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

EXPECTED_SYNC_TOOL_METRIC = (f"Llm/tool/CrewAI/crewai.tools.tool_usage:ToolUsage._use/{TOOL_NAME}", 1)
EXPECTED_ASYNC_TOOL_METRIC = (f"Llm/tool/CrewAI/crewai.tools.tool_usage:ToolUsage._ause/{TOOL_NAME}", 1)

# 10 events:
#  * 1 LlmTool
#  * 2 LlmChatCompletionSummary, one per LLM round-trip
#  * 7 LlmChatCompletionMessage across those two round-trips
EXPECTED_EVENT_COUNT = 10


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(tool_recorded_event(record_content=True)))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_tools:test_tool",
    scoped_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    rollup_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": f'{{"type": "APM-AI_TOOL", "name": "{TOOL_NAME}"}}'})
@background_task()
def test_tool(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT)
    with WithLlmCustomAttributes({"context": "attr"}):
        result = crew.kickoff()
    assert "Paris" in str(result)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(tool_recorded_event(record_content=True)))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_tools:test_tool_async",
    scoped_metrics=[EXPECTED_ASYNC_TOOL_METRIC],
    rollup_metrics=[EXPECTED_ASYNC_TOOL_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": f'{{"type": "APM-AI_TOOL", "name": "{TOOL_NAME}"}}'})
@background_task()
def test_tool_async(build_crew, crewai_llm, set_trace_info, loop):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT)
    with WithLlmCustomAttributes({"context": "attr"}):
        result = loop.run_until_complete(crew.akickoff())
    assert "Paris" in str(result)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(tool_recorded_event(record_content=False))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_tools:test_tool_no_content",
    scoped_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    rollup_metrics=[EXPECTED_SYNC_TOOL_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_tool_no_content(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT)
    result = crew.kickoff()
    assert "Paris" in str(result)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_tools:test_tool_disabled_ai_monitoring", background_task=True)
@background_task()
def test_tool_disabled_ai_monitoring(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT)
    result = crew.kickoff()
    assert "Paris" in str(result)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_tool_outside_transaction(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, tools=[get_capital], description=TOOL_PROMPT)
    result = crew.kickoff()
    assert "Paris" in str(result)
