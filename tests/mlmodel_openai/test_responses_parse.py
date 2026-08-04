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

"""responses.parse() is a distinct entry point that does not route through create which returns structured output."""

import openai
import pytest
from pydantic import BaseModel
from testing_support.fixtures import override_llm_token_callback_settings, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    add_token_counts_to_chat_events,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_sans_content,
    events_sans_llm_metadata,
    events_with_context_attrs,
    llm_token_count_callback,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute

MODEL = "gpt-5.1"
INSTRUCTIONS = "You are a text parser."
PROMPT = [
    {"role": "user", "content": "How many letters are in the word Python? Answer in one word with no formatting."}
]


responses_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "req_a23af6d131df4e958e44fd0fee47af24",
            "duration": None,  # Response time varies each test run
            "request.model": MODEL,
            "response.model": "gpt-5.1-2025-11-13",
            "response.organization": "nr-test-org",
            "request.temperature": 0.7,
            "request.max_tokens": 500,
            "response.usage.completion_tokens": 19,
            "response.usage.prompt_tokens": 64,
            "response.usage.total_tokens": 83,
            "response.choices.finish_reason": "completed",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 10000,
            "response.headers.ratelimitLimitTokens": 50000000,
            "response.headers.ratelimitResetTokens": "0s",
            "response.headers.ratelimitResetRequests": "6ms",
            "response.headers.ratelimitRemainingTokens": 49999975,
            "response.headers.ratelimitRemainingRequests": 9999,
            "vendor": "openai",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "resp_0464cf6d565af4e8006a73d0e80c50819889e3cb5edfd6b6a3-0",
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "req_a23af6d131df4e958e44fd0fee47af24",
            "span_id": None,
            "trace_id": "trace-id",
            "content": INSTRUCTIONS,
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-5.1-2025-11-13",
            "token_count": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "resp_0464cf6d565af4e8006a73d0e80c50819889e3cb5edfd6b6a3-1",
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "req_a23af6d131df4e958e44fd0fee47af24",
            "span_id": None,
            "trace_id": "trace-id",
            "content": PROMPT[0]["content"],
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-5.1-2025-11-13",
            "token_count": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "resp_0464cf6d565af4e8006a73d0e80c50819889e3cb5edfd6b6a3-2",
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "req_a23af6d131df4e958e44fd0fee47af24",
            "span_id": None,
            "trace_id": "trace-id",
            "content": '{"count":1}',
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-5.1-2025-11-13",
            "token_count": 0,
            "vendor": "openai",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


class LetterCount(BaseModel):
    count: int


@pytest.fixture(params=("sync", "async"))
def exercise(request, loop, async_openai_client, sync_openai_client):
    def _exercise():
        if request.param == "sync":
            sync_openai_client.responses.parse(
                model=MODEL,
                instructions=INSTRUCTIONS,
                input=PROMPT,
                text_format=LetterCount,
                temperature=0.7,
                max_output_tokens=500,
            )
        else:
            loop.run_until_complete(
                async_openai_client.responses.parse(
                    model=MODEL,
                    instructions=INSTRUCTIONS,
                    input=PROMPT,
                    text_format=LetterCount,
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )

    return _exercise


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(responses_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_parse:test_openai_responses_parse_with_llm_metadata",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_parse_with_llm_metadata(set_trace_info, exercise):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        exercise()


@reset_core_stats_engine()
@validate_custom_events(responses_recorded_events)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_parse:test_openai_responses_parse_with_raw_response",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_parse_with_raw_response(set_trace_info, exercise):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    exercise()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(responses_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_parse:test_openai_responses_parse_no_content",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_parse_no_content(set_trace_info, exercise):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    exercise()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_counts_to_chat_events(responses_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_parse:test_openai_responses_parse_with_token_count",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_parse_with_token_count(set_trace_info, exercise):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    exercise()


@reset_core_stats_engine()
@validate_custom_events(events_sans_llm_metadata(responses_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_parse:test_openai_responses_parse_no_llm_metadata",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_parse_no_llm_metadata(set_trace_info, exercise):
    set_trace_info()
    exercise()


@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_responses_parse:test_openai_responses_parse_disabled_ai_monitoring", background_task=True
)
@background_task()
def test_openai_responses_parse_disabled_ai_monitoring(set_trace_info, exercise):
    set_trace_info()
    exercise()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_responses_parse_outside_transaction(set_trace_info, exercise):
    exercise()
