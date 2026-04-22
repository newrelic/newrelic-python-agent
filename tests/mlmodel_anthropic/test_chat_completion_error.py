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

import anthropic
import pytest
from conftest import ANTHROPIC_VERSION_METRIC
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

PY310 = sys.version_info >= (3, 10)

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
            "vendor": "anthropic",
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
            "vendor": "anthropic",
            "ingest_source": "Python",
        },
    ),
]


@pytest.fixture(scope="session")
def chat_completion_metrics(is_create_method):
    if is_create_method:
        return [("Llm/completion/Anthropic/create", 1)]
    else:
        return [("Llm/completion/Anthropic/stream", 1)]


@pytest.fixture(scope="session")
def missing_model_error(interaction_method, is_async, is_create_method):
    if is_create_method:
        return "Missing required arguments; Expected either ('max_tokens', 'messages' and 'model') or ('max_tokens', 'messages', 'model' and 'stream') arguments to be given"
    else:
        # On Python 3.10+ the TypeError message includes the class name, but on earlier versions it does not.
        cls_name = f"{'Async' if is_async else ''}Messages."
        return f"{cls_name if PY310 else ''}stream() missing 1 required keyword-only argument: 'model'"


@dt_enabled
@reset_core_stats_engine()
def test_chat_completion_invalid_request_error_no_model(
    exercise_model, chat_completion_metrics, set_trace_info, missing_model_error
):
    @validate_error_trace_attributes("builtins:TypeError", exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": missing_model_error})
    @validate_transaction_metrics(
        name="test_chat_completion_invalid_request_error_no_model",
        scoped_metrics=chat_completion_metrics,
        rollup_metrics=chat_completion_metrics,
        custom_metrics=[(ANTHROPIC_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(events_with_context_attrs(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task(name="test_chat_completion_invalid_request_error_no_model")
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            with WithLlmCustomAttributes({"context": "attr"}):
                exercise_model(
                    # No model provided
                    messages=[{"role": "user", "content": "How many letters are in the word Python?"}],
                    max_tokens=100,
                    temperature=0.7,
                )

    _test()


@dt_enabled
@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
def test_chat_completion_invalid_request_error_no_model_no_content(
    exercise_model, chat_completion_metrics, set_trace_info, missing_model_error
):
    @validate_error_trace_attributes("builtins:TypeError", exact_attrs={"agent": {}, "intrinsic": {}, "user": {}})
    @validate_span_events(exact_agents={"error.message": missing_model_error})
    @validate_transaction_metrics(
        name="test_chat_completion_invalid_request_error_no_model_no_content",
        scoped_metrics=chat_completion_metrics,
        rollup_metrics=chat_completion_metrics,
        custom_metrics=[(ANTHROPIC_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(events_sans_content(expected_events_on_no_model_error))
    @validate_custom_event_count(count=2)
    @background_task(name="test_chat_completion_invalid_request_error_no_model_no_content")
    def _test():
        with pytest.raises(TypeError):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            exercise_model(
                # No model provided
                messages=[{"role": "user", "content": "How many letters are in the word Python?"}],
                max_tokens=100,
                temperature=0.7,
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
            "vendor": "anthropic",
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
            "vendor": "anthropic",
            "ingest_source": "Python",
        },
    ),
]

INVALID_MODEL_ERROR = "The given model doesn't exist in the requested endpoint"


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_chat_completion_invalid_request_error_invalid_model_with_token_count(
    exercise_model, chat_completion_metrics, set_trace_info, is_streaming
):
    if is_streaming:
        # Streaming endpoints return a 200 status code, but the first event is an error that will be raised.
        expected_exception_type = anthropic.APIStatusError
        expected_status_code = 200
    else:
        # The non-streaming endpoint returns a 422 status code and immediately raises an exception.
        expected_exception_type = anthropic.UnprocessableEntityError
        expected_status_code = 422

    @validate_error_trace_attributes(
        f"anthropic:{expected_exception_type.__name__}",
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {"error.code": expected_exception_type.__name__, "http.statusCode": expected_status_code},
        },
    )
    @validate_span_events(exact_agents={"error.message": INVALID_MODEL_ERROR})
    @validate_transaction_metrics(
        name="test_chat_completion_invalid_request_error_invalid_model_with_token_count",
        scoped_metrics=chat_completion_metrics,
        rollup_metrics=chat_completion_metrics,
        custom_metrics=[(ANTHROPIC_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(add_token_count_to_events(expected_events_on_invalid_model_error))
    @validate_custom_event_count(count=2)
    @background_task(name="test_chat_completion_invalid_request_error_invalid_model_with_token_count")
    def _test():
        with pytest.raises(expected_exception_type):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            exercise_model(
                model="does-not-exist",
                messages=[{"role": "user", "content": "Model does not exist."}],
                max_tokens=100,
                temperature=0.7,
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
            "request.model": "claude-4-5-sonnet",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "anthropic",
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
            "response.model": "claude-4-5-sonnet",
            "completion_id": None,
            "sequence": 0,
            "vendor": "anthropic",
            "ingest_source": "Python",
        },
    ),
]

INVALID_API_KEY_ERROR = "Unreadable token, please pass a valid token."


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
def test_chat_completion_wrong_api_key_error(
    anthropic_clients, exercise_model, chat_completion_metrics, set_trace_info, monkeypatch
):
    @validate_error_trace_attributes(
        "anthropic:BadRequestError",
        exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "BadRequestError", "http.statusCode": 400}},
    )
    @validate_span_events(exact_agents={"error.message": INVALID_API_KEY_ERROR})
    @validate_transaction_metrics(
        name="test_chat_completion_wrong_api_key_error",
        scoped_metrics=chat_completion_metrics,
        rollup_metrics=chat_completion_metrics,
        custom_metrics=[(ANTHROPIC_VERSION_METRIC, 1)],
        background_task=True,
    )
    @validate_custom_events(expected_events_on_wrong_api_key_error)
    @validate_custom_event_count(count=2)
    @background_task(name="test_chat_completion_wrong_api_key_error")
    def _test():
        with pytest.raises(anthropic.BadRequestError):
            set_trace_info()
            fake_api_key = "DEADBEEF"
            for client in anthropic_clients:
                monkeypatch.setattr(client, "api_key", fake_api_key)

            exercise_model(
                model="claude-4-5-sonnet",
                messages=[{"role": "user", "content": "Invalid API key."}],
                max_tokens=100,
                temperature=0.7,
            )

    _test()
