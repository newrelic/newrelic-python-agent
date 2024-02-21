# Copyright 2010 New Relic, Inc.
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
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
    validate_attributes,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute

disabled_custom_insights_settings = {"custom_insights_events.enabled": False}
disabled_ai_monitoring_settings = {"ai_monitoring.enabled": False}

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

chat_completion_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "response.model": "gpt-3.5-turbo-0613",
            "response.organization": "new-relic-nkmd8b",
            # Usage tokens aren't available when streaming.
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 200,
            "response.headers.ratelimitLimitTokens": 40000,
            "response.headers.ratelimitResetTokens": "180ms",
            "response.headers.ratelimitResetRequests": "11m32.334s",
            "response.headers.ratelimitRemainingTokens": 39880,
            "response.headers.ratelimitRemainingRequests": 198,
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug-0",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug-1",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug-2",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
# One summary event, one system message, one user message, and one response message from the assistant
# @validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_stream_v1:test_openai_chat_completion_sync_in_txn_with_convo_id",
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_in_txn_with_convo_id(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    generator = sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_messages,
        temperature=0.7,
        max_tokens=100,
        stream=True,
    )
    for resp in generator:
        assert resp


chat_completion_recorded_events_no_convo_id = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "response.model": "gpt-3.5-turbo-0613",
            "response.organization": "new-relic-nkmd8b",
            # Usage tokens aren't available when streaming.
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 200,
            "response.headers.ratelimitLimitTokens": 40000,
            "response.headers.ratelimitResetTokens": "180ms",
            "response.headers.ratelimitResetRequests": "11m32.334s",
            "response.headers.ratelimitRemainingTokens": 39880,
            "response.headers.ratelimitRemainingRequests": 198,
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug-0",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug-1",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-8TJ9dS50zgQM7XicE8PLnCyEihRug-2",
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openAI",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_no_convo_id)
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_stream_v1:test_openai_chat_completion_sync_in_txn_no_convo_id",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_sync_in_txn_no_convo_id(set_trace_info, sync_openai_client):
    set_trace_info()
    generator = sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_messages,
        temperature=0.7,
        max_tokens=100,
        stream=True,
    )
    for resp in generator:
        assert resp


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_chat_completion_sync_outside_txn(sync_openai_client):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    generator = sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_messages,
        temperature=0.7,
        max_tokens=100,
        stream=True,
    )
    for resp in generator:
        assert resp


@override_application_settings(disabled_custom_insights_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_chat_completion_stream_v1:test_openai_chat_completion_sync_custom_events_insights_disabled",
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_sync_custom_events_insights_disabled(set_trace_info, sync_openai_client):
    set_trace_info()
    generator = sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_messages,
        temperature=0.7,
        max_tokens=100,
        stream=True,
    )
    for resp in generator:
        assert resp


@override_application_settings(disabled_ai_monitoring_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_chat_completion_sync_ai_monitoring_disabled(sync_openai_client):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    generator = sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_messages,
        temperature=0.7,
        max_tokens=100,
        stream=True,
    )
    for resp in generator:
        assert resp


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_no_convo_id)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_stream_v1:test_openai_chat_completion_async_conversation_id_unset",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_async_conversation_id_unset(loop, set_trace_info, async_openai_client):
    set_trace_info()

    async def consumer():
        generator = await async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )
        async for resp in generator:
            assert resp

    loop.run_until_complete(consumer())


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_stream_v1:test_openai_chat_completion_async_conversation_id_set",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_transaction_metrics(
    name="test_chat_completion_stream_v1:test_openai_chat_completion_async_conversation_id_set",
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_conversation_id_set(loop, set_trace_info, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    async def consumer():
        generator = await async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )
        async for resp in generator:
            assert resp

    loop.run_until_complete(consumer())


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_chat_completion_async_outside_transaction(loop, async_openai_client):
    async def consumer():
        generator = await async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )
        async for resp in generator:
            assert resp

    loop.run_until_complete(consumer())


@override_application_settings(disabled_custom_insights_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_chat_completion_stream_v1:test_openai_chat_completion_async_disabled_custom_event_settings",
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_async_disabled_custom_event_settings(loop, async_openai_client):
    async def consumer():
        generator = await async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )
        async for resp in generator:
            assert resp

    loop.run_until_complete(consumer())


@override_application_settings(disabled_ai_monitoring_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_chat_completion_async_disabled_ai_monitoring_settings(loop, async_openai_client):
    async def consumer():
        generator = await async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )
        async for resp in generator:
            assert resp

    loop.run_until_complete(consumer())
