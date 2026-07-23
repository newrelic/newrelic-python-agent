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

from testing_support.fixtures import dt_enabled, reset_core_stats_engine
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes

from ._test_agent import PROMPT, build_agent

# 4 events from the Bedrock Converse round-trip:
#  * 1 LlmChatCompletionSummary
#  * 3 LlmChatCompletionMessage (system / user / assistant)
# No other events yet as MAF instrumentation is not written.
EXPECTED_EVENT_COUNT = 4


@dt_enabled
@reset_core_stats_engine()
@validate_custom_event_count(EXPECTED_EVENT_COUNT)
@validate_transaction_metrics("mlmodel_agentframework.bedrock.test_agent:test_agent", background_task=True)
@background_task()
def test_agent(exercise_agent, bedrock_client, set_trace_info):
    set_trace_info()
    agent = build_agent(bedrock_client)
    with WithLlmCustomAttributes({"context": "attr"}):
        response = exercise_agent(agent, PROMPT)

    assert "Paris" in response.text


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_event_count(EXPECTED_EVENT_COUNT)
@validate_transaction_metrics("mlmodel_agentframework.bedrock.test_agent:test_agent_no_content", background_task=True)
@background_task()
def test_agent_no_content(exercise_agent, bedrock_client, set_trace_info):
    set_trace_info()
    agent = build_agent(bedrock_client)
    response = exercise_agent(agent, PROMPT)

    assert "Paris" in response.text


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(0)
@validate_transaction_metrics(
    "mlmodel_agentframework.bedrock.test_agent:test_agent_disabled_ai_monitoring", background_task=True
)
@background_task()
def test_agent_disabled_ai_monitoring(exercise_agent, bedrock_client, set_trace_info):
    set_trace_info()
    agent = build_agent(bedrock_client)
    response = exercise_agent(agent, PROMPT)

    assert "Paris" in response.text


@reset_core_stats_engine()
@validate_custom_event_count(0)
def test_agent_outside_transaction(exercise_agent, bedrock_client, set_trace_info):
    set_trace_info()
    agent = build_agent(bedrock_client)
    response = exercise_agent(agent, PROMPT)

    assert "Paris" in response.text
