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
import pytest
import openai
from conftest import (  # pylint: disable=E0611
    add_token_count_to_event,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_sans_content,
    llm_token_count_callback_success,
    llm_token_count_callback_negative_return_val,
    llm_token_count_callback_non_int_return_val,
)
from testing_support.fixtures import (
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
from newrelic.api.ml_model import set_llm_token_count_callback

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

chat_completion_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "response.model": "gpt-3.5-turbo-0613",
            "response.organization": "new-relic-nkmd8b",
            "response.usage.completion_tokens": 82,
            "response.usage.total_tokens": 108,
            "response.usage.prompt_tokens": 26,
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
            "response.headers.ratelimitLimitTokensUsageBased": 40000,
            "response.headers.ratelimitResetTokensUsageBased": "180ms",
            "response.headers.ratelimitRemainingTokensUsageBased": 39880,
            "vendor": "openai",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openai",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_sync_in_txn_with_llm_metadata",
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_in_txn_with_llm_metadata(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_sync_in_txn_with_llm_metadata_no_content",
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_in_txn_with_llm_metadata_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
    )


@pytest.mark.parametrize(
    "llm_token_callback",
    [
        llm_token_count_callback_success,
        llm_token_count_callback_negative_return_val,
        llm_token_count_callback_non_int_return_val,
    ],
)
@reset_core_stats_engine()
def test_openai_chat_completion_sync_with_token_count_callback(set_trace_info, sync_openai_client, llm_token_callback):
    if llm_token_callback.__name__ == "llm_token_count_callback_success":
        expected_events = add_token_count_to_event(chat_completion_recorded_events)
    else:
        expected_events = chat_completion_recorded_events

    @validate_custom_event_count(count=4)
    @validate_custom_events(expected_events)
    @validate_transaction_metrics(
        "test_chat_completion_v1:test_openai_chat_completion_sync_with_token_count_callback.<locals>._test",
        scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
        rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        set_llm_token_count_callback(llm_token_callback)

        sync_openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )

    _test()


chat_completion_recorded_events_no_llm_metadata = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "response.model": "gpt-3.5-turbo-0613",
            "response.organization": "new-relic-nkmd8b",
            "response.usage.completion_tokens": 82,
            "response.usage.total_tokens": 108,
            "response.usage.prompt_tokens": 26,
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
            "response.headers.ratelimitLimitTokensUsageBased": 40000,
            "response.headers.ratelimitResetTokensUsageBased": "180ms",
            "response.headers.ratelimitRemainingTokensUsageBased": 39880,
            "vendor": "openai",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "request_id": "f8d0f53b6881c5c0a3698e55f8f410ac",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "212 degrees Fahrenheit is equal to 100 degrees Celsius.",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-3.5-turbo-0613",
            "vendor": "openai",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_no_llm_metadata)
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_sync_in_txn_no_llm_metadata",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_sync_in_txn_no_llm_metadata(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_chat_completion_sync_outside_txn(sync_openai_client):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_chat_completion_sync_ai_monitoring_disabled(sync_openai_client):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
    )


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events_no_llm_metadata)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_async_no_llm_metadata",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_async_no_llm_metadata(loop, set_trace_info, async_openai_client):
    set_trace_info()

    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )
    )


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_async_with_llm_metadata",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_with_llm_metadata(loop, set_trace_info, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(chat_completion_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_async_with_llm_metadata_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_with_llm_metadata_no_content(loop, set_trace_info, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")

    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )
    )


@pytest.mark.parametrize(
    "llm_token_callback",
    [
        llm_token_count_callback_success,
        llm_token_count_callback_negative_return_val,
        llm_token_count_callback_non_int_return_val,
    ],
)
@reset_core_stats_engine()
def test_openai_chat_completion_async_with_token_count_callback(
    set_trace_info, loop, async_openai_client, llm_token_callback
):
    if llm_token_callback.__name__ == "llm_token_count_callback_success":
        expected_events = add_token_count_to_event(chat_completion_recorded_events)
    else:
        expected_events = chat_completion_recorded_events

    @validate_custom_event_count(count=4)
    @validate_custom_events(expected_events)
    @validate_transaction_metrics(
        "test_chat_completion_v1:test_openai_chat_completion_async_with_token_count_callback.<locals>._test",
        scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
        rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        set_llm_token_count_callback(llm_token_callback)

        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
            )
        )

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_chat_completion_async_outside_transaction(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_chat_completion_async_ai_monitoring_disabled(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )
    )


@reset_core_stats_engine()
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=3)
# @validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_no_usage_data(set_trace_info, sync_openai_client, loop):
    # Only testing that there are events, and there was no exception raised
    set_trace_info()
    sync_openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=({"role": "user", "content": "No usage data"},), temperature=0.7, max_tokens=100
    )


@reset_core_stats_engine()
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=3)
# @validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_no_usage_data(set_trace_info, async_openai_client, loop):
    # Only testing that there are events, and there was no exception raised
    set_trace_info()
    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=({"role": "user", "content": "No usage data"},),
            temperature=0.7,
            max_tokens=100,
        )
    )
