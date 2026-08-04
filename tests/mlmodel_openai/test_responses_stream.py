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

"""
Streaming tests for OpenAI Responses API instrumentation (``responses.create(stream=True)``).

See test_responses.py for the recording workflow and the note on wildcarded (``None``) expected
values. Streaming summaries additionally carry ``time_to_first_token``; token usage is reconstructed
from the terminal ``response.completed`` event.
"""

import openai
import pytest
from conftest import OPENAI_VERSION
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    disabled_ai_monitoring_streaming_settings,
    events_sans_content,
    events_with_context_attrs,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute

SKIP_IF_NO_OPENAI_WITH_STREAMING_RESPONSE = pytest.mark.skipif(
    OPENAI_VERSION < (1, 8), reason="OpenAI does not support .with_streaming_response. until v1.8"
)

MODEL = "gpt-5.1"
INSTRUCTIONS = "You are a text parser."
PROMPT = [
    {"role": "user", "content": "How many letters are in the word Python? Answer in one word with no formatting."}
]

responses_stream_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": None,
            "duration": None,
            "request.model": MODEL,
            "response.model": "gpt-5.1-2025-11-13",
            "response.organization": "nr-test-org",
            "request.temperature": 0.7,
            "request.max_tokens": 500,
            "response.usage.completion_tokens": 11,
            "response.usage.prompt_tokens": 33,
            "response.usage.total_tokens": 44,
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
            "time_to_first_token": None,  # varies each test run
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
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
            "id": None,
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
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
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "six",
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


def _consume_sync(client):
    generator = client.responses.create(
        model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500, stream=True
    )
    for _ in generator:
        pass


def _consume_async(client, loop):
    async def _run():
        generator = await client.responses.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500, stream=True
        )
        async for _ in generator:
            pass

    loop.run_until_complete(_run())


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(responses_stream_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_stream:test_openai_responses_stream_sync_with_llm_metadata",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_stream_sync_with_llm_metadata(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        _consume_sync(sync_openai_client)


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(responses_stream_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_stream:test_openai_responses_stream_sync_no_content",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_stream_sync_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    _consume_sync(sync_openai_client)


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(responses_stream_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_responses_stream:test_openai_responses_stream_async_with_llm_metadata",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_responses_stream_async_with_llm_metadata(set_trace_info, async_openai_client, loop):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        _consume_async(async_openai_client, loop)


@reset_core_stats_engine()
@disabled_ai_monitoring_streaming_settings
@validate_custom_event_count(count=0)
@background_task()
def test_openai_responses_stream_sync_disabled_streaming(set_trace_info, sync_openai_client):
    # With streaming monitoring disabled we do not proxy the stream, so no LLM events are recorded.
    set_trace_info()
    _consume_sync(sync_openai_client)


@reset_core_stats_engine()
@disabled_ai_monitoring_settings
@validate_custom_event_count(count=0)
@background_task()
def test_openai_responses_stream_sync_disabled_ai_monitoring(set_trace_info, sync_openai_client):
    set_trace_info()
    _consume_sync(sync_openai_client)


def _with_streaming_response_create_kwargs(stream_set, stream_val):
    kwargs = {
        "model": MODEL,
        "instructions": INSTRUCTIONS,
        "input": PROMPT,
        "temperature": 0.7,
        "max_output_tokens": 500,
    }
    if stream_set:
        kwargs["stream"] = stream_val
    return kwargs


# `.with_streaming_response.` is not yet instrumented, so it emits no LLM events. The tests below
# assert that current behavior (count=0). Instrumenting it is future work.
@SKIP_IF_NO_OPENAI_WITH_STREAMING_RESPONSE
@reset_core_stats_engine()
@pytest.mark.parametrize("iter_method", ["iter_lines", "iter_bytes", "iter_text"])
@pytest.mark.parametrize("stream_set, stream_val", [(False, None), (True, True), (True, False)])
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_responses_stream:test_openai_responses_sync_with_streaming_response", background_task=True
)
@background_task()
def test_openai_responses_sync_with_streaming_response(
    set_trace_info, sync_openai_client, iter_method, stream_set, stream_val
):
    set_trace_info()
    create_kwargs = _with_streaming_response_create_kwargs(stream_set, stream_val)
    with sync_openai_client.responses.with_streaming_response.create(**create_kwargs) as response:
        for _ in getattr(response, iter_method)():
            pass


@SKIP_IF_NO_OPENAI_WITH_STREAMING_RESPONSE
@reset_core_stats_engine()
@pytest.mark.parametrize("iter_method", ["iter_lines", "iter_bytes", "iter_text"])
@pytest.mark.parametrize("stream_set, stream_val", [(False, None), (True, True), (True, False)])
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_responses_stream:test_openai_responses_async_with_streaming_response", background_task=True
)
@background_task()
def test_openai_responses_async_with_streaming_response(
    set_trace_info, async_openai_client, loop, iter_method, stream_set, stream_val
):
    set_trace_info()
    create_kwargs = _with_streaming_response_create_kwargs(stream_set, stream_val)

    async def _run():
        async with async_openai_client.responses.with_streaming_response.create(**create_kwargs) as response:
            async for _ in getattr(response, iter_method)():
                pass

    loop.run_until_complete(_run())
