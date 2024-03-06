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

import copy

import openai
import pytest
from testing_support.fixtures import (
    dt_enabled,
    override_application_settings,
    reset_core_stats_engine,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name


def events_sans_content(event):
    new_event = copy.deepcopy(event)
    for _event in new_event:
        if "content" in _event[1]:
            del _event[1]["content"]
    return new_event


_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

expected_events_on_no_model_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "transaction_id": "transaction-id",
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "",  # No model in this test case
            "response.organization": "",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 2,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "request_id": "",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "response.model": "",
            "completion_id": None,
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "request_id": "",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "response.model": "",
            "sequence": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Missing required arguments; Expected either ('messages' and 'model') or ('messages', 'model' and 'stream') arguments to be given",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_invalid_request_error_no_model",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_no_model_error)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model(set_trace_info, sync_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        sync_openai_client.chat.completions.create(
            messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )


@reset_core_stats_engine()
@override_application_settings({"ai_monitoring.record_content.enabled": False})
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Missing required arguments; Expected either ('messages' and 'model') or ('messages', 'model' and 'stream') arguments to be given",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_invalid_request_error_no_model_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_no_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_no_content(set_trace_info, sync_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        sync_openai_client.chat.completions.create(
            messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Missing required arguments; Expected either ('messages' and 'model') or ('messages', 'model' and 'stream') arguments to be given",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_invalid_request_error_no_model_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_no_model_error)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_async(loop, set_trace_info, async_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
            )
        )


@reset_core_stats_engine()
@override_application_settings({"ai_monitoring.record_content.enabled": False})
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Missing required arguments; Expected either ('messages' and 'model') or ('messages', 'model' and 'stream') arguments to be given",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_invalid_request_error_no_model_async_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_no_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_async_no_content(loop, set_trace_info, async_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
            )
        )


expected_events_on_invalid_model_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "transaction_id": "transaction-id",
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "response.organization": "",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "request_id": "",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Model does not exist.",
            "role": "user",
            "response.model": "",
            "completion_id": None,
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.NotFoundError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "error.code": "model_not_found",
            "http.statusCode": 404,
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_invalid_request_error_invalid_model",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_invalid_model_error)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model(set_trace_info, sync_openai_client):
    with pytest.raises(openai.NotFoundError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        sync_openai_client.chat.completions.create(
            model="does-not-exist",
            messages=({"role": "user", "content": "Model does not exist."},),
            temperature=0.7,
            max_tokens=100,
        )


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.NotFoundError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "error.code": "model_not_found",
            "http.statusCode": 404,
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_invalid_request_error_invalid_model_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_invalid_model_error)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model_async(loop, set_trace_info, async_openai_client):
    with pytest.raises(openai.NotFoundError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                model="does-not-exist",
                messages=({"role": "user", "content": "Model does not exist."},),
                temperature=0.7,
                max_tokens=100,
            )
        )


expected_events_on_wrong_api_key_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "response.organization": "",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "request_id": "",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Invalid API key.",
            "role": "user",
            "completion_id": None,
            "response.model": "",
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
            "error.code": "invalid_api_key",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_wrong_api_key_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_wrong_api_key_error)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_wrong_api_key_error(monkeypatch, set_trace_info, sync_openai_client):
    with pytest.raises(openai.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(sync_openai_client, "api_key", "DEADBEEF")
        sync_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=({"role": "user", "content": "Invalid API key."},),
            temperature=0.7,
            max_tokens=100,
        )


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
            "error.code": "invalid_api_key",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error_v1:test_chat_completion_wrong_api_key_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_wrong_api_key_error)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_wrong_api_key_error_async(loop, monkeypatch, set_trace_info, async_openai_client):
    with pytest.raises(openai.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(async_openai_client, "api_key", "DEADBEEF")
        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=({"role": "user", "content": "Invalid API key."},),
                temperature=0.7,
                max_tokens=100,
            )
        )
