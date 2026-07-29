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

from _test_workflow_agents import (
    WORKFLOW_PROMPT,
    WORKFLOW_STEP1_AGENT_NAME,
    WORKFLOW_STEP2_AGENT_NAME,
    build_workflow,
    workflow_recorded_events,
)
from conftest import EXPECTED_VERSION_METRICS
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

EXPECTED_METRICS = [
    (f"Llm/agent/GoogleADK/run_async/{WORKFLOW_STEP1_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{WORKFLOW_STEP2_AGENT_NAME}", 1),
]

EXPECTED_STEP1_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{WORKFLOW_STEP1_AGENT_NAME}"}}'
EXPECTED_STEP2_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{WORKFLOW_STEP2_AGENT_NAME}"}}'

STEP1_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{WORKFLOW_STEP1_AGENT_NAME}"
STEP2_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{WORKFLOW_STEP2_AGENT_NAME}"

# 8 events:
#  * 2 LlmAgent child events
#  * 6 LLM events from 2 Gemini round-trips (Input/Output/Summary)
#  * No workflow event because Workflow is not instrumented itself.
EXPECTED_EVENT_COUNT = 8


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(workflow_recorded_events))
@validate_custom_event_count(EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_workflow_agents:test_workflow_agent",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1, exact_intrinsics={"name": STEP1_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_STEP1_SUBCOMPONENT}
)
@validate_span_events(
    count=1, exact_intrinsics={"name": STEP2_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_STEP2_SUBCOMPONENT}
)
@background_task()
def test_workflow_agent(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_workflow()
    with WithLlmCustomAttributes({"context": "attr"}):
        events = exercise_agent(agent, WORKFLOW_PROMPT)

    assert events


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(workflow_recorded_events)
@validate_custom_event_count(EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_workflow_agents:test_workflow_agent_no_content",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1, exact_intrinsics={"name": STEP1_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_STEP1_SUBCOMPONENT}
)
@validate_span_events(
    count=1, exact_intrinsics={"name": STEP2_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_STEP2_SUBCOMPONENT}
)
@background_task()
def test_workflow_agent_no_content(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_workflow()
    events = exercise_agent(agent, WORKFLOW_PROMPT)

    assert events


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(0)
@validate_transaction_metrics("test_workflow_agents:test_workflow_agent_disabled_ai_monitoring", background_task=True)
@background_task()
def test_workflow_agent_disabled_ai_monitoring(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_workflow()
    events = exercise_agent(agent, WORKFLOW_PROMPT)

    assert events


@reset_core_stats_engine()
@validate_custom_event_count(0)
def test_workflow_agent_outside_transaction(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_workflow()
    events = exercise_agent(agent, WORKFLOW_PROMPT)

    assert events
