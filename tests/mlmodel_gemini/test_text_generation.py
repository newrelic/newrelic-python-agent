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

import google.genai
from testing_support.fixtures import override_llm_token_callback_settings, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
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

text_generation_recorded_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "gemini-2.0-flash",
            "response.model": "gemini-2.0-flash",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "STOP",
            "vendor": "gemini",
            "ingest_source": "Python",
            "response.number_of_messages": 2,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "How many letters are in the word Python?",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "gemini-2.0-flash",
            "vendor": "gemini",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "content": 'There are **6** letters in the word "Python".\n',
            "role": "model",
            "completion_id": None,
            "sequence": 1,
            "response.model": "gemini-2.0-flash",
            "vendor": "gemini",
            "is_response": True,
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
# Expect one summary event, one message event for the input, and message event for the output for each send_message_call
@validate_custom_event_count(count=6)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_multi_text_generation",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_multi_text_generation(gemini_dev_client, set_trace_info):
    chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
    chat.send_message(
        message="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )
    chat.send_message(
        message="Who invented the Python programming language?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_sync_generate_content",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_sync_generate_content(gemini_dev_client, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        gemini_dev_client.models.generate_content(
            model="gemini-2.0-flash",
            contents="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_sync_with_llm_metadata",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_sync_with_llm_metadata(gemini_dev_client, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
        chat.send_message(
            message="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_sync_no_content",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_sync_no_content(gemini_dev_client, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
    chat.send_message(
        message="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_sync_with_token_count",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_sync_with_token_count(gemini_dev_client, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
    chat.send_message(
        message="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@reset_core_stats_engine()
@validate_custom_events(events_sans_llm_metadata(text_generation_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    "test_text_generation:test_gemini_text_generation_sync_no_llm_metadata",
    scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    background_task=True,
)
@background_task()
def test_gemini_text_generation_sync_no_llm_metadata(gemini_dev_client, set_trace_info):
    set_trace_info()

    chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
    chat.send_message(
        message="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_gemini_text_generation_sync_outside_txn(gemini_dev_client):
    chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
    chat.send_message(
        message="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_gemini_text_generation_sync_ai_monitoring_disabled(gemini_dev_client):
    chat = gemini_dev_client.chats.create(model="gemini-2.0-flash")
    chat.send_message(
        message="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_async_generate_content",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_async_generate_content(gemini_dev_client, loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        loop.run_until_complete(
            gemini_dev_client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents="How many letters are in the word Python?",
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )
        )


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_async_with_llm_metadata",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_async_with_llm_metadata(gemini_dev_client, loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")
    with WithLlmCustomAttributes({"context": "attr"}):
        chat = gemini_dev_client.aio.chats.create(model="gemini-2.0-flash")
        loop.run_until_complete(
            chat.send_message(
                message="How many letters are in the word Python?",
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )
        )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_async_no_content",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_async_no_content(gemini_dev_client, loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    chat = gemini_dev_client.aio.chats.create(model="gemini-2.0-flash")
    loop.run_until_complete(
        chat.send_message(
            message="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )
    )


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(text_generation_recorded_events))
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    name="test_text_generation:test_gemini_text_generation_async_with_token_count",
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_text_generation_async_with_token_count(gemini_dev_client, loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")

    chat = gemini_dev_client.aio.chats.create(model="gemini-2.0-flash")
    loop.run_until_complete(
        chat.send_message(
            message="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )
    )


@reset_core_stats_engine()
@validate_custom_events(events_sans_llm_metadata(text_generation_recorded_events))
# One summary event, one system message, one user message, and one response message from the assistant
@validate_custom_event_count(count=3)
@validate_transaction_metrics(
    "test_text_generation:test_gemini_text_generation_async_no_llm_metadata",
    scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    background_task=True,
)
@background_task()
def test_gemini_text_generation_async_no_llm_metadata(gemini_dev_client, loop, set_trace_info):
    set_trace_info()

    chat = gemini_dev_client.aio.chats.create(model="gemini-2.0-flash")
    loop.run_until_complete(
        chat.send_message(
            message="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_gemini_text_generation_async_outside_txn(gemini_dev_client, loop):
    chat = gemini_dev_client.aio.chats.create(model="gemini-2.0-flash")
    loop.run_until_complete(
        chat.send_message(
            message="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_gemini_text_generation_async_ai_monitoring_disabled(gemini_dev_client, loop):
    chat = gemini_dev_client.aio.chats.create(model="gemini-2.0-flash")
    loop.run_until_complete(
        chat.send_message(
            message="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )
    )
