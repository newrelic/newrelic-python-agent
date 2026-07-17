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

from _test_parallel_agent import (
    LEFT_AGENT_NAME,
    PARALLEL_AGENT_NAME,
    PARALLEL_PROMPT,
    RIGHT_AGENT_NAME,
    build_parallel,
    parallel_recorded_events,
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
    (f"Llm/agent/GoogleADK/run_async/{PARALLEL_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{LEFT_AGENT_NAME}", 1),
    (f"Llm/agent/GoogleADK/run_async/{RIGHT_AGENT_NAME}", 1),
]

EXPECTED_WORKFLOW_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{PARALLEL_AGENT_NAME}"}}'
EXPECTED_LEFT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{LEFT_AGENT_NAME}"}}'
EXPECTED_RIGHT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{RIGHT_AGENT_NAME}"}}'

WORKFLOW_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{PARALLEL_AGENT_NAME}"
LEFT_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{LEFT_AGENT_NAME}"
RIGHT_SPAN_NAME = f"Llm/agent/GoogleADK/run_async/{RIGHT_AGENT_NAME}"

# 9 events:
#  * 1 LlmAgent workflow event
#  * 2 LlmAgent child events
#  * 6 LLM events from 2 Gemini round-trips (Input/Output/Summary)
EXPECTED_EVENT_COUNT = 9


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(parallel_recorded_events))
@validate_custom_event_count(EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_parallel_agent:test_parallel_agent",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1,
    exact_intrinsics={"name": WORKFLOW_SPAN_NAME},
    exact_agents={"subcomponent": EXPECTED_WORKFLOW_SUBCOMPONENT},
)
@validate_span_events(
    count=1, exact_intrinsics={"name": LEFT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_LEFT_SUBCOMPONENT}
)
@validate_span_events(
    count=1, exact_intrinsics={"name": RIGHT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_RIGHT_SUBCOMPONENT}
)
@background_task()
def test_parallel_agent(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_parallel()
    with WithLlmCustomAttributes({"context": "attr"}):
        events = exercise_agent(agent, PARALLEL_PROMPT)

    assert events


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(parallel_recorded_events)
@validate_custom_event_count(EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_parallel_agent:test_parallel_agent_no_content",
    scoped_metrics=EXPECTED_METRICS,
    rollup_metrics=EXPECTED_METRICS,
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(
    count=1,
    exact_intrinsics={"name": WORKFLOW_SPAN_NAME},
    exact_agents={"subcomponent": EXPECTED_WORKFLOW_SUBCOMPONENT},
)
@validate_span_events(
    count=1, exact_intrinsics={"name": LEFT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_LEFT_SUBCOMPONENT}
)
@validate_span_events(
    count=1, exact_intrinsics={"name": RIGHT_SPAN_NAME}, exact_agents={"subcomponent": EXPECTED_RIGHT_SUBCOMPONENT}
)
@background_task()
def test_parallel_agent_no_content(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_parallel()
    events = exercise_agent(agent, PARALLEL_PROMPT)

    assert events


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(0)
@validate_transaction_metrics("test_parallel_agent:test_parallel_agent_disabled_ai_monitoring", background_task=True)
@background_task()
def test_parallel_agent_disabled_ai_monitoring(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_parallel()
    events = exercise_agent(agent, PARALLEL_PROMPT)

    assert events


@reset_core_stats_engine()
@validate_custom_event_count(0)
def test_parallel_agent_outside_transaction(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_parallel()
    events = exercise_agent(agent, PARALLEL_PROMPT)

    assert events
