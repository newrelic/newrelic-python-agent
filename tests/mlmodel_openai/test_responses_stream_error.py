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

import openai
import pytest
from testing_support.fixtures import dt_enabled, reset_core_stats_engine
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    events_sans_content,
    events_with_context_attrs,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name

INVALID_MODEL = "does-not-exist-nr-test"
EXPECTED_ERROR = openai.BadRequestError
INSTRUCTIONS = "You are a text parser."
PROMPT = [
    {"role": "user", "content": "How many letters are in the word Python? Answer in one word with no formatting."}
]

expected_events_on_invalid_model_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "timestamp": None,
            "llm.context": "attr",
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,
            "request.model": INVALID_MODEL,
            "request.temperature": 0.7,
            "request.max_tokens": 500,
            "response.number_of_messages": 2,
            "response.organization": "nr-test-org",
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "timestamp": None,
            "llm.context": "attr",
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": INSTRUCTIONS,
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "token_count": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "timestamp": None,
            "llm.context": "attr",
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": PROMPT[0]["content"],
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "token_count": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_invalid_model_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_invalid_model_error(set_trace_info, sync_openai_client):
    set_trace_info()
    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            generator = sync_openai_client.responses.create(
                model=INVALID_MODEL,
                instructions=INSTRUCTIONS,
                input=PROMPT,
                temperature=0.7,
                max_output_tokens=500,
                stream=True,
            )
            for _ in generator:
                pass


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_invalid_model_error_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_invalid_model_error_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            generator = sync_openai_client.responses.create(
                model=INVALID_MODEL,
                instructions=INSTRUCTIONS,
                input=PROMPT,
                temperature=0.7,
                max_output_tokens=500,
                stream=True,
            )
            for _ in generator:
                pass


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_invalid_model_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_invalid_model_error_async(loop, set_trace_info, async_openai_client):
    set_trace_info()

    async def _run():
        generator = await async_openai_client.responses.create(
            model=INVALID_MODEL,
            instructions=INSTRUCTIONS,
            input=PROMPT,
            temperature=0.7,
            max_output_tokens=500,
            stream=True,
        )
        async for _ in generator:
            pass

    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            loop.run_until_complete(_run())


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_invalid_model_error_no_content_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_invalid_model_error_no_content_async(loop, set_trace_info, async_openai_client):
    set_trace_info()

    async def _run():
        generator = await async_openai_client.responses.create(
            model=INVALID_MODEL,
            instructions=INSTRUCTIONS,
            input=PROMPT,
            temperature=0.7,
            max_output_tokens=500,
            stream=True,
        )
        async for _ in generator:
            pass

    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            loop.run_until_complete(_run())
