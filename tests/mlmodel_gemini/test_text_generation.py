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
import pytest
from conftest import GEMINI_VERSION_METRIC
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


@pytest.fixture
def text_generation_events(is_streaming):
    events = [
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
                "content": 'There are 6 letters in the word "Python".\n',
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

    if is_streaming:
        # Only valid for streaming, and varies each test run
        events[0][1]["time_to_first_token"] = None

    return events


@pytest.fixture(scope="session")
def text_generation_metrics(is_streaming):
    if is_streaming:
        return [("Llm/completion/Gemini/generate_content_stream", 1)]
    else:
        return [("Llm/completion/Gemini/generate_content", 1)]


@reset_core_stats_engine()
def test_gemini_text_generation(exercise_text_model, text_generation_metrics, set_trace_info, text_generation_events):
    # Expect one summary event, one message event for the input, and message event for the output
    @validate_custom_events(events_with_context_attrs(text_generation_events))
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_gemini_text_generation",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_text_generation")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        with WithLlmCustomAttributes({"context": "attr"}):
            exercise_text_model(
                model="gemini-2.0-flash",
                contents="How many letters are in the word Python?",
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )

    _test()


@reset_core_stats_engine()
def test_gemini_multi_text_generation(exercise_text_model, text_generation_metrics, set_trace_info):
    # Double all the metric counts for this test as we run the model twice
    text_generation_metrics = [(m[0], m[1] * 2) for m in text_generation_metrics]

    # Expect one summary event, one message event for the input, and message event for the output for each send_message_call
    @validate_custom_event_count(count=6)
    @validate_transaction_metrics(
        name="test_gemini_multi_text_generation",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_multi_text_generation")
    def _test():
        set_trace_info()
        exercise_text_model(
            model="gemini-2.0-flash",
            contents="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )
        exercise_text_model(
            model="gemini-2.0-flash",
            contents="How many letters are in the word Python?",
            # contents="Who invented the Python programming language?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )

    _test()


@reset_core_stats_engine()
def test_gemini_text_generation_with_llm_metadata(
    exercise_text_model, text_generation_metrics, set_trace_info, text_generation_events
):
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_gemini_text_generation_with_llm_metadata",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_text_generation_with_llm_metadata")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        with WithLlmCustomAttributes({"context": "attr"}):
            exercise_text_model(
                model="gemini-2.0-flash",
                contents="How many letters are in the word Python?",
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_gemini_text_generation_no_content(
    exercise_text_model, text_generation_metrics, set_trace_info, text_generation_events
):
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_gemini_text_generation_no_content",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_text_generation_no_content")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        exercise_text_model(
            model="gemini-2.0-flash",
            contents="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_gemini_text_generation_with_token_count(
    exercise_text_model, text_generation_metrics, set_trace_info, text_generation_events
):
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_gemini_text_generation_with_token_count",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_gemini_text_generation_with_token_count")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        exercise_text_model(
            model="gemini-2.0-flash",
            contents="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )

    _test()


@reset_core_stats_engine()
def test_gemini_text_generation_no_llm_metadata(
    exercise_text_model, text_generation_metrics, set_trace_info, text_generation_events
):
    # One summary event, one system message, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_gemini_text_generation_no_llm_metadata",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @background_task(name="test_gemini_text_generation_no_llm_metadata")
    def _test():
        set_trace_info()
        exercise_text_model(
            model="gemini-2.0-flash",
            contents="How many letters are in the word Python?",
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_gemini_text_generation_outside_txn(exercise_text_model):
    exercise_text_model(
        model="gemini-2.0-flash",
        contents="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_gemini_text_generation_ai_monitoring_disabled(exercise_text_model):
    exercise_text_model(
        model="gemini-2.0-flash",
        contents="How many letters are in the word Python?",
        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
    )
