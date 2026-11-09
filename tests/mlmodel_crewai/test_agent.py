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

from _test_agents import agent_recorded_events
from conftest import AGENT_NAME, AGENT_PROMPT, EXPECTED_VERSION_METRICS
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

EXPECTED_AGENT_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.execute_task/{AGENT_NAME}", 1)
EXPECTED_AGENT_ASYNC_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.aexecute_task/{AGENT_NAME}", 1)

# 5 events:
#  * 1 LlmAgent for the agent's execute_task (the Crew itself records none)
#  * 1 LlmChatCompletionSummary for the single LLM round-trip
#  * 3 LlmChatCompletionMessage from that round-trip (system, user, assistant answer)
EXPECTED_EVENT_COUNT = 5

AGENT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{AGENT_NAME}"}}'


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(agent_recorded_events()))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent:test_agent_execute_task",
    scoped_metrics=[EXPECTED_AGENT_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": AGENT_SUBCOMPONENT})
@background_task()
def test_agent_execute_task(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT)
    with WithLlmCustomAttributes({"context": "attr"}):
        result = crew.kickoff()
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(agent_recorded_events()))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent:test_agent_aexecute_task",
    scoped_metrics=[EXPECTED_AGENT_ASYNC_METRIC],
    rollup_metrics=[EXPECTED_AGENT_ASYNC_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": AGENT_SUBCOMPONENT})
@background_task()
def test_agent_aexecute_task(build_crew, crewai_llm, set_trace_info, loop):
    """Crew.akickoff is the only path that reaches Agent.aexecute_task."""
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT)
    with WithLlmCustomAttributes({"context": "attr"}):
        result = loop.run_until_complete(crew.akickoff())
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(agent_recorded_events())
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent:test_agent_no_content",
    scoped_metrics=[EXPECTED_AGENT_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_agent_no_content(build_crew, crewai_llm, set_trace_info):
    """LlmAgent has no content fields, so record_content has nothing to strip from these events."""
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT)
    result = crew.kickoff()
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_agent:test_agent_disabled_ai_monitoring", background_task=True)
@background_task()
def test_agent_disabled_ai_monitoring(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT)
    result = crew.kickoff()
    assert str(result)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_agent_outside_transaction(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=AGENT_PROMPT)
    result = crew.kickoff()
    assert str(result)
