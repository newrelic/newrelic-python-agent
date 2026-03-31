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
            "token_count": 0,
            "completion_id": None,
            "sequence": 0,
            "vendor": "gemini",
            "ingest_source": "Python",
        },
    ),
]


def test_text_generation_invalid_request_error_no_model(gemini_dev_client, set_trace_info):
    if sys.version_info < (3, 10):
        error_message = "generate_content() missing 1 required keyword-only argument: 'model'"
    else:
        error_message = "Models.generate_content() missing 1 required keyword-only argument: 'model'"

    # No model provided
    @dt_enabled
    @reset_core_stats_engine()
    @validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": error_message})
    @validate_transaction_metrics(
        "test_text_generation_error:test_text_generation_invalid_request_error_no_model.<locals>._test",
        scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        background_task=True,
    )
    @validate_custom_events(events_with_context_attrs(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task()
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            with WithLlmCustomAttributes({"context": "attr"}):
                gemini_dev_client.models.generate_content(
                    # no model
                    contents=["How many letters are in the word Python?"],
                    config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
                )

    _test()


def test_text_generation_invalid_request_error_no_model_no_content(gemini_dev_client, set_trace_info):
    if sys.version_info < (3, 10):
        error_message = "generate_content() missing 1 required keyword-only argument: 'model'"
    else:
        error_message = "Models.generate_content() missing 1 required keyword-only argument: 'model'"

    @dt_enabled
    @disabled_ai_monitoring_record_content_settings
    @reset_core_stats_engine()
    @validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": error_message})
    @validate_transaction_metrics(
        "test_text_generation_error:test_text_generation_invalid_request_error_no_model_no_content.<locals>._test",
        scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        background_task=True,
    )
    @validate_custom_events(events_sans_content(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task()
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")

            gemini_dev_client.models.generate_content(
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
            "token_count": 0,
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
    "test_text_generation_error:test_text_generation_invalid_request_error_invalid_model_chat",
    scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_invalid_model_error)
@validate_custom_event_count(count=2)
@background_task()
def test_text_generation_invalid_request_error_invalid_model_chat(gemini_dev_client, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        chat = gemini_dev_client.chats.create(model="does-not-exist")
        chat.send_message(
            message=["Model does not exist."],
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )


expected_events_on_wrong_api_key_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "timestamp": None,
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "gemini-flash-2.0",
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
            "token_count": 0,
            "response.model": "gemini-flash-2.0",
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
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "INVALID_ARGUMENT", "http.statusCode": 400}},
)
@validate_span_events(exact_agents={"error.message": "API key not valid. Please pass a valid API key."})
@validate_transaction_metrics(
    "test_text_generation_error:test_text_generation_wrong_api_key_error",
    scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_wrong_api_key_error)
@validate_custom_event_count(count=2)
@background_task()
def test_text_generation_wrong_api_key_error(gemini_dev_client, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        gemini_dev_client._api_client.api_key = "DEADBEEF"
        gemini_dev_client.models.generate_content(
            model="gemini-flash-2.0",
            contents=["Invalid API key."],
            config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
        )


def test_text_generation_async_invalid_request_error_no_model(gemini_dev_client, loop, set_trace_info):
    if sys.version_info < (3, 10):
        error_message = "generate_content() missing 1 required keyword-only argument: 'model'"
    else:
        error_message = "Models.generate_content() missing 1 required keyword-only argument: 'model'"

    # No model provided
    @dt_enabled
    @reset_core_stats_engine()
    @validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": error_message})
    @validate_transaction_metrics(
        "test_text_generation_error:test_text_generation_async_invalid_request_error_no_model.<locals>._test",
        scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        background_task=True,
    )
    @validate_custom_events(events_with_context_attrs(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task()
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            with WithLlmCustomAttributes({"context": "attr"}):
                loop.run_until_complete(
                    gemini_dev_client.models.generate_content(
                        # no model
                        contents=["How many letters are in the word Python?"],
                        config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
                    )
                )

    _test()


def test_text_generation_async_invalid_request_error_no_model_no_content(gemini_dev_client, loop, set_trace_info):
    if sys.version_info < (3, 10):
        error_message = "generate_content() missing 1 required keyword-only argument: 'model'"
    else:
        error_message = "Models.generate_content() missing 1 required keyword-only argument: 'model'"

    @dt_enabled
    @disabled_ai_monitoring_record_content_settings
    @reset_core_stats_engine()
    @validate_error_trace_attributes(callable_name(TypeError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": error_message})
    @validate_transaction_metrics(
        "test_text_generation_error:test_text_generation_async_invalid_request_error_no_model_no_content.<locals>._test",
        scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
        background_task=True,
    )
    @validate_custom_events(events_sans_content(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task()
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            loop.run_until_complete(
                gemini_dev_client.models.generate_content(
                    # no model
                    contents=["How many letters are in the word Python?"],
                    config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
                )
            )

    _test()


@dt_enabled
@reset_core_stats_engine()
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
    "test_text_generation_error:test_text_generation_async_invalid_request_error_invalid_model_chat",
    scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_invalid_model_error)
@validate_custom_event_count(count=2)
@background_task()
def test_text_generation_async_invalid_request_error_invalid_model_chat(gemini_dev_client, loop, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        chat = gemini_dev_client.chats.create(model="does-not-exist")
        loop.run_until_complete(
            chat.send_message(
                message=["Model does not exist."],
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )
        )


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "INVALID_ARGUMENT", "http.statusCode": 400}},
)
@validate_span_events(exact_agents={"error.message": "API key not valid. Please pass a valid API key."})
@validate_transaction_metrics(
    "test_text_generation_error:test_text_generation_async_wrong_api_key_error",
    scoped_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    rollup_metrics=[("Llm/completion/Gemini/generate_content", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_wrong_api_key_error)
@validate_custom_event_count(count=2)
@background_task()
def test_text_generation_async_wrong_api_key_error(gemini_dev_client, loop, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        gemini_dev_client._api_client.api_key = "DEADBEEF"
        loop.run_until_complete(
            gemini_dev_client.models.generate_content(
                model="gemini-flash-2.0",
                contents=["Invalid API key."],
                config=google.genai.types.GenerateContentConfig(max_output_tokens=100, temperature=0.7),
            )
        )
