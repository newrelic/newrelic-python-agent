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
from _test_agents import agent_recorded_events
from conftest import AGENT_NAME, CREW_PROMPT, EXPECTED_VERSION_METRICS
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import disabled_ai_monitoring_settings
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

NUM_AGENTS = 2

# One agent-level span per task, and one crew-level span per run.
EXPECTED_AGENT_METRICS = [
    (f"Llm/agent/CrewAI/crewai.agent.core:Agent.execute_task/{AGENT_NAME}_{i}", 1) for i in range(NUM_AGENTS)
]
EXPECTED_AGENT_ASYNC_METRICS = [
    (f"Llm/agent/CrewAI/crewai.agent.core:Agent.aexecute_task/{AGENT_NAME}_{i}", 1) for i in range(NUM_AGENTS)
]

# 2 LlmAgent events, one per agent task, plus the LLM events from the two sequential round-trips,
# one per task. The Crew records none of its own.
EXPECTED_EVENT_COUNT = 10

KICKOFF_INPUTS = {"topic": "geography"}


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events(num_agents=NUM_AGENTS))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_crew:test_crew_kickoff",
    scoped_metrics=[*EXPECTED_AGENT_METRICS],
    rollup_metrics=[*EXPECTED_AGENT_METRICS],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_crew_kickoff(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=CREW_PROMPT, num_agents=NUM_AGENTS, num_tasks=NUM_AGENTS)
    result = crew.kickoff()
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events(num_agents=NUM_AGENTS))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_crew:test_crew_kickoff_async",
    scoped_metrics=[*EXPECTED_AGENT_METRICS],
    rollup_metrics=[*EXPECTED_AGENT_METRICS],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_crew_kickoff_async(build_crew, crewai_llm, set_trace_info, loop):
    """
    kickoff_async runs the crew through asyncio.to_thread(self.kickoff, ...), so every event here
    depends on the trace being carried onto that worker thread.
    """
    set_trace_info()
    crew = build_crew(crewai_llm, description=CREW_PROMPT, num_agents=NUM_AGENTS, num_tasks=NUM_AGENTS)
    result = loop.run_until_complete(crew.kickoff_async())
    assert str(result)


@pytest.mark.parametrize("pass_inputs_as", ("positional", "keyword"))
@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events(num_agents=NUM_AGENTS))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_crew:test_crew_kickoff_async_inputs_untouched",
    scoped_metrics=[*EXPECTED_AGENT_METRICS],
    rollup_metrics=[*EXPECTED_AGENT_METRICS],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@background_task()
def test_crew_kickoff_async_inputs_untouched(build_crew, crewai_llm, set_trace_info, loop, pass_inputs_as):
    """
    The trace rides to the worker thread on the inputs, but CrewAI must only ever see the caller's
    own inputs, and the caller's dict must not be modified.
    """
    set_trace_info()
    crew = build_crew(crewai_llm, description=CREW_PROMPT, num_agents=NUM_AGENTS, num_tasks=NUM_AGENTS)

    seen_inputs = []

    def record_inputs(inputs):
        seen_inputs.append(inputs)
        return inputs

    crew.before_kickoff_callbacks.append(record_inputs)

    inputs = dict(KICKOFF_INPUTS)
    if pass_inputs_as == "positional":
        coro = crew.kickoff_async(inputs)
    else:
        coro = crew.kickoff_async(inputs=inputs)
    result = loop.run_until_complete(coro)
    assert str(result)

    assert inputs == KICKOFF_INPUTS
    assert type(inputs) is dict
    assert seen_inputs == [KICKOFF_INPUTS]
    assert type(seen_inputs[0]) is dict
    assert type(crew._inputs) is dict


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events(agent_recorded_events(num_agents=NUM_AGENTS))
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_crew:test_crew_akickoff",
    scoped_metrics=[*EXPECTED_AGENT_ASYNC_METRICS],
    rollup_metrics=[*EXPECTED_AGENT_ASYNC_METRICS],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_crew_akickoff(build_crew, crewai_llm, set_trace_info, loop):
    """akickoff is natively async end to end, reaching Agent.aexecute_task rather than execute_task."""
    set_trace_info()
    crew = build_crew(crewai_llm, description=CREW_PROMPT, num_agents=NUM_AGENTS, num_tasks=NUM_AGENTS)
    result = loop.run_until_complete(crew.akickoff())
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_crew:test_crew_disabled_ai_monitoring", background_task=True)
@background_task()
def test_crew_disabled_ai_monitoring(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=CREW_PROMPT, num_agents=NUM_AGENTS, num_tasks=NUM_AGENTS)
    result = crew.kickoff()
    assert str(result)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_crew_outside_transaction(build_crew, crewai_llm, set_trace_info):
    set_trace_info()
    crew = build_crew(crewai_llm, description=CREW_PROMPT, num_agents=NUM_AGENTS, num_tasks=NUM_AGENTS)
    result = crew.kickoff()
    assert str(result)
