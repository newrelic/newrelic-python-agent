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
from openai.types.responses import Response
from openai.types.responses.response_error import ResponseError
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

# A valid model for the in-band failure case, where the request itself is well-formed but the
# server reports the failure in the response body rather than as an HTTP error.
MODEL = "gpt-5.1"
FAILED_RESPONSE_ID = "resp_nr_test_failed"
FAILED_RESPONSE_MODEL = "gpt-5.1-2025-11-13"
FAILED_ERROR_CODE = "server_error"
FAILED_ERROR_MESSAGE = "The model failed to generate a response."
# An in-band failure surfaces as a synthesized openai.APIError, not the SDK's HTTP error types.
FAILED_EXPECTED_ERROR = openai.APIError

# The openai SDK depends on a vendored httpx (imported as "httpx2" in recent versions); resolve it
# from the SDK rather than importing httpx directly so this stays correct across SDK versions.
_httpx = getattr(_openai_base_client, "httpx2", None) or _openai_base_client.httpx

# Served by a mock transport, so VCR must not try to replay or record requests to this host.
MOCK_HOST = "localhost"


def _failed_post(*args, **kwargs):
    """A Responses API Response whose status is 'failed' with a nested error, as the server
    returns for an in-band failure (e.g. a background response that terminates in failure)."""
    return Response.model_construct(
        id=FAILED_RESPONSE_ID,
        status="failed",
        error=ResponseError(code=FAILED_ERROR_CODE, message=FAILED_ERROR_MESSAGE),
        model=FAILED_RESPONSE_MODEL,
        output=[],
    )


async def _async_failed_post(*args, **kwargs):
    return _failed_post()


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
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
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
    "test_responses_error:test_openai_responses_invalid_model_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_invalid_model_error(set_trace_info, sync_openai_client):
    set_trace_info()
    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            sync_openai_client.responses.create(
                model=INVALID_MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
            )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_invalid_model_error_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_invalid_model_error_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        sync_openai_client.responses.create(
            model=INVALID_MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
        )


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_invalid_model_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_invalid_model_error_async(loop, set_trace_info, async_openai_client):
    set_trace_info()
    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            loop.run_until_complete(
                async_openai_client.responses.create(
                    model=INVALID_MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
                )
            )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(callable_name(EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_invalid_model_error_no_content_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_invalid_model_error_no_content_async(loop, set_trace_info, async_openai_client):
    set_trace_info()
    with pytest.raises(EXPECTED_ERROR):
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            async_openai_client.responses.create(
                model=INVALID_MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
            )
        )


# === In-band failures: a 200 response whose status is "failed" ===
# The SDK does not raise for these, so create() returns normally; the agent must still record the
# turn as an error. These are mocked because a synchronous responses.create() essentially never
# returns status "failed" against the live API (failures come back as HTTP errors), so there is no
# real interaction to record.


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_failed_status_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_failed_status_error(monkeypatch, set_trace_info, sync_openai_client):
    set_trace_info()
    monkeypatch.setattr(sync_openai_client.responses, "_post", _failed_post)
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    # No pytest.raises: the SDK returns a Response with status "failed" rather than raising.
    with WithLlmCustomAttributes({"context": "attr"}):
        sync_openai_client.responses.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
        )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_failed_status_error_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_failed_status_error_no_content(monkeypatch, set_trace_info, sync_openai_client):
    set_trace_info()
    monkeypatch.setattr(sync_openai_client.responses, "_post", _failed_post)
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    sync_openai_client.responses.create(
        model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
    )


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_failed_status_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_failed_status_error_async(monkeypatch, loop, set_trace_info, async_openai_client):
    set_trace_info()

    monkeypatch.setattr(async_openai_client.responses, "_post", _async_failed_post)
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    with WithLlmCustomAttributes({"context": "attr"}):
        loop.run_until_complete(
            async_openai_client.responses.create(
                model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
            )
        )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_failed_status_error_no_content_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_failed_status_error_no_content_async(monkeypatch, loop, set_trace_info, async_openai_client):
    set_trace_info()

    monkeypatch.setattr(async_openai_client.responses, "_post", _async_failed_post)
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    loop.run_until_complete(
        async_openai_client.responses.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
        )
    )


# === In-band failure returned through .with_raw_response ===
# Unlike the cases above, this goes through the real SDK response parsing (a LegacyAPIResponse
# wrapping the HTTP response) instead of patching _post, so it covers the raw-response unwrapping.


@pytest.mark.vcr(ignore_hosts=[MOCK_HOST])
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(FAILED_EXPECTED_ERROR), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_transaction_metrics(
    "test_responses_error:test_openai_responses_failed_status_error_with_raw_response",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_failed_response))
@validate_custom_event_count(count=3)
@background_task()
def test_openai_responses_failed_status_error_with_raw_response(set_trace_info, openai_api_key):
    set_trace_info()
    body = json.dumps(
        {
            "id": FAILED_RESPONSE_ID,
            "object": "response",
            "created_at": 0,
            "model": FAILED_RESPONSE_MODEL,
            "status": "failed",
            "error": {"code": FAILED_ERROR_CODE, "message": FAILED_ERROR_MESSAGE},
            "output": [],
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
        }
    ).encode()

    def handler(request):
        return _httpx.Response(200, content=body, headers={"content-type": "application/json"})

    client = openai.OpenAI(
        api_key=openai_api_key,
        base_url=f"http://{MOCK_HOST}/v1",
        http_client=_httpx.Client(transport=_httpx.MockTransport(handler)),
    )
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    with WithLlmCustomAttributes({"context": "attr"}):
        client.responses.with_raw_response.create(
            model=MODEL, instructions=INSTRUCTIONS, input=PROMPT, temperature=0.7, max_output_tokens=500
        )
