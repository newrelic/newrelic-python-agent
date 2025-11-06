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
from testing_support.fixtures import (
    override_application_settings,
    override_llm_token_callback_settings,
    reset_core_stats_engine,
    validate_attributes,
)
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    disabled_ai_monitoring_streaming_settings,
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
from newrelic.api.transaction import accept_distributed_trace_headers, add_custom_attribute

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

chat_completion_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "req_983c5abb07aa4f51b858f855fc614d08",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-5.1",
            "response.model": "gpt-5.1-2025-11-13",
            "response.organization": "nr-test-org",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "stop",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 15000,
            "response.headers.ratelimitLimitTokens": 40000000,
            "response.headers.ratelimitResetTokens": "0s",
            "response.headers.ratelimitResetRequests": "4ms",
            "response.headers.ratelimitRemainingTokens": 39999979,
            "response.headers.ratelimitRemainingRequests": 14999,
            "vendor": "openai",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-CoLlpfFdbk9D0AbjizzpQ8hMwX9AY-0",
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "req_983c5abb07aa4f51b858f855fc614d08",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gpt-5.1-2025-11-13",
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-CoLlpfFdbk9D0AbjizzpQ8hMwX9AY-1",
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "req_983c5abb07aa4f51b858f855fc614d08",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gpt-5.1-2025-11-13",
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": "chatcmpl-CoLlpfFdbk9D0AbjizzpQ8hMwX9AY-2",
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "req_983c5abb07aa4f51b858f855fc614d08",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "212\u00b0F is 100\u00b0C.",
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "gpt-5.1-2025-11-13",
            "vendor": "openai",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_sync_with_llm_metadata",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_with_llm_metadata(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        sync_openai_client.chat.completions.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_sync_with_llm_metadata_with_raw_response",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_with_llm_metadata_with_raw_response(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    sync_openai_client.chat.completions.with_raw_response.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_sync_no_content",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    sync_openai_client.chat.completions.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_sync_with_token_count",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_sync_with_token_count(set_trace_info, sync_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    sync_openai_client.chat.completions.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@reset_core_stats_engine()
@validate_custom_events(events_sans_llm_metadata(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_sync_no_llm_metadata",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_sync_no_llm_metadata(set_trace_info, sync_openai_client):
    set_trace_info()

    sync_openai_client.chat.completions.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_streaming_settings
@validate_custom_events(events_sans_llm_metadata(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_sync_stream_monitoring_disabled",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_sync_stream_monitoring_disabled(set_trace_info, sync_openai_client):
    set_trace_info()

    sync_openai_client.chat.completions.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_chat_completion_sync_outside_txn(sync_openai_client):
    sync_openai_client.chat.completions.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_chat_completion_sync_ai_monitoring_disabled(sync_openai_client):
    sync_openai_client.chat.completions.create(
        model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
    )


@reset_core_stats_engine()
@validate_custom_events(events_sans_llm_metadata(chat_completion_recorded_events))
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
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_streaming_settings
@validate_custom_events(events_sans_llm_metadata(chat_completion_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_async_stream_monitoring_disabled",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@background_task()
def test_openai_chat_completion_async_stream_monitoring_disabled(loop, set_trace_info, async_openai_client):
    set_trace_info()

    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )
    )


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(chat_completion_recorded_events))
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_async_with_llm_metadata",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_with_llm_metadata(loop, set_trace_info, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    with WithLlmCustomAttributes({"context": "attr"}):
        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                model="gpt-5.1",
                messages=_test_openai_chat_completion_messages,
                temperature=0.7,
                max_completion_tokens=100,
            )
        )


@reset_core_stats_engine()
@validate_custom_events(chat_completion_recorded_events)
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    "test_chat_completion_v1:test_openai_chat_completion_async_with_llm_metadata_with_raw_response",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_with_llm_metadata_with_raw_response(loop, set_trace_info, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    loop.run_until_complete(
        async_openai_client.chat.completions.with_raw_response.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
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
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_with_llm_metadata_no_content(loop, set_trace_info, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )
    )


@pytest.mark.parametrize("partial_granularity_type", ("reduced", "essential", "compact"))
def test_openai_chat_completion_async_in_txn_with_token_count_partial_granularity_dt(
    partial_granularity_type, set_trace_info, loop, async_openai_client
):
    @reset_core_stats_engine()
    @disabled_ai_monitoring_record_content_settings
    @validate_custom_events(events_sans_content(chat_completion_recorded_events))
    @validate_custom_event_count(count=4)
    @validate_transaction_metrics(
        "test_chat_completion_v1:test_openai_chat_completion_async_in_txn_with_token_count_partial_granularity_dt.<locals>._test",
        scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
        rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
        custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @override_application_settings(
        {
            "distributed_tracing.sampler.full_granularity.enabled": False,
            "distributed_tracing.sampler.partial_granularity.enabled": True,
            "distributed_tracing.sampler.partial_granularity.type": partial_granularity_type,
            "distributed_tracing.sampler.partial_granularity.remote_parent_sampled": "always_on",
            "span_events.enabled": True,
        }
    )
    @background_task()
    def _test():
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        accept_distributed_trace_headers({"traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"})
        set_trace_info()
        loop.run_until_complete(
            async_openai_client.chat.completions.create(
                model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
            )
        )

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(chat_completion_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_chat_completion_v1:test_openai_chat_completion_async_in_txn_with_token_count",
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_in_txn_with_token_count(set_trace_info, loop, async_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_chat_completion_async_outside_transaction(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_chat_completion_async_ai_monitoring_disabled(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-5.1", messages=_test_openai_chat_completion_messages, temperature=0.7, max_completion_tokens=100
        )
    )


@reset_core_stats_engine()
# One summary event and one user message (no assistant message is recorded)
@validate_custom_event_count(count=2)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_no_usage_data(set_trace_info, sync_openai_client):
    # Only testing that there are events, and there was no exception raised
    set_trace_info()
    sync_openai_client.chat.completions.create(
        model="gpt-5.1",
        messages=({"role": "user", "content": "No usage data"},),
        temperature=0.7,
        max_completion_tokens=100,
    )


@reset_core_stats_engine()
# One summary event and one user message (no assistant message is recorded)
@validate_custom_event_count(count=2)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_chat_completion_async_no_usage_data(set_trace_info, async_openai_client, loop):
    # Only testing that there are events, and there was no exception raised
    set_trace_info()
    loop.run_until_complete(
        async_openai_client.chat.completions.create(
            model="gpt-5.1",
            messages=({"role": "user", "content": "No usage data"},),
            temperature=0.7,
            max_completion_tokens=100,
        )
    )
