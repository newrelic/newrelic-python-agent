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


import sys

import google.genai
import pytest
from conftest import GEMINI_VERSION_METRIC
from testing_support.fixtures import dt_enabled, override_llm_token_callback_settings, reset_core_stats_engine
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
    disabled_ai_monitoring_record_content_settings,
    events_sans_content,
    events_with_context_attrs,
    llm_token_count_callback,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name

expected_events_on_no_model_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "gemini",
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
            "content": "How many letters are in the word Python?",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "vendor": "gemini",
            "ingest_source": "Python",
        },
    ),
]


@pytest.fixture(scope="session")
def text_generation_metrics(is_streaming):
    if is_streaming:
        return [("Llm/completion/Gemini/generate_content_stream", 1)]
    else:
        return [("Llm/completion/Gemini/generate_content", 1)]


@pytest.fixture(scope="session")
def model_error_msg(is_async, is_chat, is_streaming):
    if is_chat:
        pytest.skip("Only valid for direct model calls")

    class_name = "AsyncModels" if is_async else "Models"
    method = "generate_content" if not is_streaming else "generate_content_stream"
    if sys.version_info < (3, 10):
        return f"{method}() missing 1 required keyword-only argument: 'model'"
    else:
        return f"{class_name}.{method}() missing 1 required keyword-only argument: 'model'"


def test_text_generation_invalid_request_error_no_model(
    exercise_text_model, text_generation_metrics, set_trace_info, model_error_msg
):
    # No model provided
    @dt_enabled
    @reset_core_stats_engine()
    @validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": model_error_msg})
    @validate_transaction_metrics(
        name="test_text_generation_invalid_request_error_no_model",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(events_with_context_attrs(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task(name="test_text_generation_invalid_request_error_no_model")
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            with WithLlmCustomAttributes({"context": "attr"}):
                exercise_text_model(
                    # no model
                    contents=["How many letters are in the word Python?"],
                    config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
                )

    _test()


def test_text_generation_invalid_request_error_no_model_no_content(
    exercise_text_model, text_generation_metrics, set_trace_info, model_error_msg
):
    @dt_enabled
    @disabled_ai_monitoring_record_content_settings
    @reset_core_stats_engine()
    @validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": model_error_msg})
    @validate_transaction_metrics(
        name="test_text_generation_invalid_request_error_no_model_no_content",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(events_sans_content(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task(name="test_text_generation_invalid_request_error_no_model_no_content")
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            exercise_text_model(
                # no model
                contents=["How many letters are in the word Python?"],
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )

    _test()


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
            "request.model": "does-not-exist",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "gemini",
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
            "content": "Model does not exist.",
            "role": "user",
            "completion_id": None,
            "response.model": "does-not-exist",
            "sequence": 0,
            "vendor": "gemini",
            "ingest_source": "Python",
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_text_generation_invalid_request_error_invalid_model_with_token_count(
    exercise_text_model, text_generation_metrics, set_trace_info
):
    @validate_error_trace_attributes(
        callable_name(google.genai.errors.ClientError),
        exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "NOT_FOUND", "http.statusCode": 404}},
    )
    @validate_span_events(
        exact_agents={
            "error.message": "models/does-not-exist is not found for API version v1beta, or is not supported for generateContent. Call ListModels to see the list of available models and their supported methods."
        }
    )
    @validate_transaction_metrics(
        name="test_text_generation_invalid_request_error_invalid_model_with_token_count",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(add_token_count_to_events(expected_events_on_invalid_model_error))
    @validate_custom_event_count(count=2)
    @background_task(name="test_text_generation_invalid_request_error_invalid_model_with_token_count")
    def _test():
        with pytest.raises(google.genai.errors.ClientError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            exercise_text_model(
                model="does-not-exist",
                contents=["Model does not exist."],
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )

    _test()


expected_events_on_wrong_api_key_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "gemini-2.0-flash",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "gemini",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "timestamp": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "Invalid API key.",
            "role": "user",
            "response.model": "gemini-2.0-flash",
            "completion_id": None,
            "sequence": 0,
            "vendor": "gemini",
            "ingest_source": "Python",
        },
    ),
]


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
def test_text_generation_wrong_api_key_error(
    gemini_dev_client, exercise_text_model, text_generation_metrics, set_trace_info
):
    @validate_error_trace_attributes(
        callable_name(google.genai.errors.ClientError),
        exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "INVALID_ARGUMENT", "http.statusCode": 400}},
    )
    @validate_span_events(exact_agents={"error.message": "API key not valid. Please pass a valid API key."})
    @validate_transaction_metrics(
        name="test_text_generation_wrong_api_key_error",
        scoped_metrics=text_generation_metrics,
        rollup_metrics=text_generation_metrics,
        custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(expected_events_on_wrong_api_key_error)
    @validate_custom_event_count(count=2)
    @background_task(name="test_text_generation_wrong_api_key_error")
    def _test():
        with pytest.raises(google.genai.errors.ClientError):
            set_trace_info()
            fake_api_key = "DEADBEEF"
            gemini_dev_client._api_client.api_key = fake_api_key
            gemini_dev_client._api_client._http_options.headers["x-goog-api-key"] = fake_api_key
            exercise_text_model(
                model="gemini-2.0-flash",
                contents=["Invalid API key."],
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )

    _test()
