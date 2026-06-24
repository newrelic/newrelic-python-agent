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
from conftest import GOOGLEADK_VERSION
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

EXPECTED_AGENT_METRIC = (f"Llm/agent/GoogleADK/run_async/{AGENT_NAME}", 1)
EXPECTED_SUPPORTABILITY_METRIC = (f"Supportability/Python/ML/GoogleADK/{GOOGLEADK_VERSION}", 1)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(agent_recorded_event))
@validate_custom_event_count(count=4)  # Agent, Input, Output, Summary.
@validate_transaction_metrics(
    "test_agent:test_agent",
    scoped_metrics=[EXPECTED_AGENT_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC],
    custom_metrics=[EXPECTED_SUPPORTABILITY_METRIC],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
@background_task()
def test_agent(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent()
    with WithLlmCustomAttributes({"context": "attr"}):
        events = exercise_agent(agent, PROMPT)

    assert len(events) == 1
    assert events[0].content.parts[0].text == "Paris"


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(agent_recorded_event)
@validate_custom_event_count(count=4)  # Agent, Input, Output, Summary.
@validate_transaction_metrics(
    "test_agent:test_agent_no_content",
    scoped_metrics=[EXPECTED_AGENT_METRIC],
    rollup_metrics=[EXPECTED_AGENT_METRIC],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": '{"type": "APM-AI_AGENT", "name": "my_agent"}'})
@background_task()
def test_agent_no_content(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent()
    events = exercise_agent(agent, PROMPT)

    assert len(events) == 1
    assert events[0].content.parts[0].text == "Paris"


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_agent:test_agent_disabled_ai_monitoring", background_task=True)
@background_task()
def test_agent_disabled_ai_monitoring(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent()
    events = exercise_agent(agent, PROMPT)

    assert len(events) == 1
    assert events[0].content.parts[0].text == "Paris"


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_agent_outside_transaction(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent()
    events = exercise_agent(agent, PROMPT)

    assert len(events) == 1
    assert events[0].content.parts[0].text == "Paris"
