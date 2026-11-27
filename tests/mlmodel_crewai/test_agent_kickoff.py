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

from _test_agents import agent_event
from conftest import AGENT_NAME, EXPECTED_VERSION_METRICS, KICKOFF_PROMPT
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import disabled_ai_monitoring_settings
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

EXPECTED_KICKOFF_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.kickoff/{AGENT_NAME}", 1)
EXPECTED_KICKOFF_ASYNC_METRIC = (f"Llm/agent/CrewAI/crewai.agent.core:Agent.kickoff_async/{AGENT_NAME}", 1)

# 5 events: 1 LlmAgent + 1 LlmChatCompletionSummary + 3 LlmChatCompletionMessage
EXPECTED_EVENT_COUNT = 5

AGENT_SUBCOMPONENT = f'{{"type": "APM-AI_AGENT", "name": "{AGENT_NAME}"}}'


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events([agent_event()])
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent_kickoff:test_agent_kickoff",
    scoped_metrics=[EXPECTED_KICKOFF_METRIC],
    rollup_metrics=[EXPECTED_KICKOFF_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": AGENT_SUBCOMPONENT})
@background_task()
def test_agent_kickoff(build_agent, crewai_llm, set_trace_info):
    set_trace_info()
    agent = build_agent(crewai_llm)
    result = agent.kickoff(KICKOFF_PROMPT)
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events([agent_event()])
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent_kickoff:test_agent_kickoff_async",
    scoped_metrics=[EXPECTED_KICKOFF_ASYNC_METRIC],
    rollup_metrics=[EXPECTED_KICKOFF_ASYNC_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": AGENT_SUBCOMPONENT})
@background_task()
def test_agent_kickoff_async(build_agent, crewai_llm, set_trace_info, loop):
    set_trace_info()
    agent = build_agent(crewai_llm)
    result = loop.run_until_complete(agent.kickoff_async(KICKOFF_PROMPT))
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events([agent_event()])
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent_kickoff:test_agent_akickoff_records_once",
    scoped_metrics=[EXPECTED_KICKOFF_ASYNC_METRIC],
    rollup_metrics=[EXPECTED_KICKOFF_ASYNC_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": AGENT_SUBCOMPONENT})
@background_task()
def test_agent_akickoff_records_once(build_agent, crewai_llm, set_trace_info, loop):
    """
    akickoff just awaits kickoff_async, so only kickoff_async is instrumented. The event count and
    the single agent span here both double if akickoff is ever wrapped as well.
    """
    set_trace_info()
    agent = build_agent(crewai_llm)
    result = loop.run_until_complete(agent.akickoff(KICKOFF_PROMPT))
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@validate_custom_events([agent_event()])
@validate_custom_event_count(count=EXPECTED_EVENT_COUNT)
@validate_transaction_metrics(
    "test_agent_kickoff:test_agent_kickoff_inside_event_loop",
    scoped_metrics=[EXPECTED_KICKOFF_ASYNC_METRIC],
    rollup_metrics=[EXPECTED_KICKOFF_ASYNC_METRIC],
    custom_metrics=EXPECTED_VERSION_METRICS,
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@validate_span_events(count=1, exact_agents={"subcomponent": AGENT_SUBCOMPONENT})
@background_task()
def test_agent_kickoff_inside_event_loop(build_agent, crewai_llm, set_trace_info, loop):
    """
    Inside a running loop Agent.kickoff returns kickoff_async's coroutine unawaited. Exactly one
    event and one span should come out of awaiting it.
    """
    set_trace_info()
    agent = build_agent(crewai_llm)

    async def run():
        return await agent.kickoff(KICKOFF_PROMPT)

    result = loop.run_until_complete(run())
    assert str(result)


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics("test_agent_kickoff:test_agent_kickoff_disabled_ai_monitoring", background_task=True)
@background_task()
def test_agent_kickoff_disabled_ai_monitoring(build_agent, crewai_llm, set_trace_info):
    set_trace_info()
    agent = build_agent(crewai_llm)
    result = agent.kickoff(KICKOFF_PROMPT)
    assert str(result)


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_agent_kickoff_outside_transaction(build_agent, crewai_llm, set_trace_info):
    set_trace_info()
    agent = build_agent(crewai_llm)
    result = agent.kickoff(KICKOFF_PROMPT)
    assert str(result)
