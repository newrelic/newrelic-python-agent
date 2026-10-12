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

import json

import openai
import openai._base_client as _openai_base_client
import pytest
from openai._streaming import AsyncStream, Stream
from openai.types.responses import ResponseStreamEvent
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

# A valid model for the in-band failure case: the request is well-formed, but the stream reports
# the failure via a response.failed event rather than an HTTP error.
MODEL = "gpt-5.1"
FAILED_RESPONSE_ID = "resp_nr_test_failed_stream"
FAILED_RESPONSE_MODEL = "gpt-5.1-2025-11-13"
FAILED_ERROR_CODE = "server_error"
FAILED_ERROR_MESSAGE = "The model failed to generate a response."
# An in-band failure surfaces as a synthesized openai.APIError, not the SDK's HTTP error types.
FAILED_EXPECTED_ERROR = openai.APIError

# The openai SDK depends on a vendored httpx (imported as "httpx2" in recent versions); resolve it
# from the SDK rather than importing httpx directly so this stays correct across SDK versions.
_httpx = getattr(_openai_base_client, "httpx2", None) or _openai_base_client.httpx

_FAILED_STREAM_SSE = (
    b"event: response.failed\ndata: "
    + json.dumps(
        {
            "type": "response.failed",
            "sequence_number": 1,
            "response": {
                "id": FAILED_RESPONSE_ID,
                "object": "response",
                "created_at": 1784592277,
                "status": "failed",
                "error": {"code": FAILED_ERROR_CODE, "message": FAILED_ERROR_MESSAGE},
                "model": FAILED_RESPONSE_MODEL,
                "output": [],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "usage": {"input_tokens": 33, "output_tokens": 0, "total_tokens": 33},
            },
        }
    ).encode()
    + b"\n\n"
)


def _failed_sse_response():
    return _httpx.Response(200, content=_FAILED_STREAM_SSE, headers={"content-type": "text/event-stream"})


def _build_failed_stream(client):
    """A real openai.Stream that yields a single response.failed event, as the server sends for an
    in-band failure. Building a real Stream keeps the agent's Stream._iter_events wrapper in play."""
    return Stream(cast_to=ResponseStreamEvent, response=_failed_sse_response(), client=client)


def _build_failed_async_stream(client):
    return AsyncStream(cast_to=ResponseStreamEvent, response=_failed_sse_response(), client=client)


expected_events_on_failed_response = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,
            "request.model": MODEL,
            "request.temperature": 0.7,
            "request.max_tokens": 500,
            "response.number_of_messages": 2,
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": f"{FAILED_RESPONSE_ID}-0",
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": INSTRUCTIONS,
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": FAILED_RESPONSE_MODEL,
            "token_count": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": f"{FAILED_RESPONSE_ID}-1",
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": PROMPT[0]["content"],
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": FAILED_RESPONSE_MODEL,
            "token_count": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
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


# === In-band failures: a response.failed event mid-stream ===
# The stream ends normally after a response.failed event (no exception is raised), so the agent
# must record the turn as an error rather than a success. These are mocked because a live stream
# does not reliably terminate in a failed state on demand, leaving no real interaction to record.


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_failed_status_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_failed_status_error(monkeypatch, set_trace_info, sync_openai_client):
    set_trace_info()
    monkeypatch.setattr(
        sync_openai_client.responses, "_post", lambda *args, **kwargs: _build_failed_stream(sync_openai_client)
    )
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    # No pytest.raises: the stream ends normally after the response.failed event.
    with WithLlmCustomAttributes({"context": "attr"}):
        generator = sync_openai_client.responses.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500, stream=True
        )
        for _ in generator:
            pass


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_failed_status_error_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_failed_status_error_no_content(monkeypatch, set_trace_info, sync_openai_client):
    set_trace_info()
    monkeypatch.setattr(
        sync_openai_client.responses, "_post", lambda *args, **kwargs: _build_failed_stream(sync_openai_client)
    )
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    generator = sync_openai_client.responses.create(
        model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500, stream=True
    )
    for _ in generator:
        pass


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_failed_status_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_failed_status_error_async(monkeypatch, loop, set_trace_info, async_openai_client):
    set_trace_info()

    async def _failed_post(*args, **kwargs):
        return _build_failed_async_stream(async_openai_client)

    monkeypatch.setattr(async_openai_client.responses, "_post", _failed_post)

    async def _run():
        generator = await async_openai_client.responses.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500, stream=True
        )
        async for _ in generator:
            pass

    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    with WithLlmCustomAttributes({"context": "attr"}):
        loop.run_until_complete(_run())


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_stream_error:test_openai_responses_stream_failed_status_error_no_content_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_stream_failed_status_error_no_content_async(
    monkeypatch, loop, set_trace_info, async_openai_client
):
    set_trace_info()

    async def _failed_post(*args, **kwargs):
        return _build_failed_async_stream(async_openai_client)

    monkeypatch.setattr(async_openai_client.responses, "_post", _failed_post)

    async def _run():
        generator = await async_openai_client.responses.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500, stream=True
        )
        async for _ in generator:
            pass

    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    loop.run_until_complete(_run())
