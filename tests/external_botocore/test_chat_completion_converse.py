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

import botocore.exceptions
import pytest
from conftest import BOTOCORE_VERSION
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
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name

chat_completion_expected_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "duration": None,  # Response time varies each test run
            "request.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.choices.finish_reason": "max_tokens",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 3,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "c20d345e-6878-4778-b674-6b187bae8ecf",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "To convert 212°F to Celsius, we can use the formula:\n\nC = (F - 32) × 5/9\n\nWhere:\nC is the temperature in Celsius\nF is the temperature in Fahrenheit\n\nPlugging in 212°F, we get:\n\nC = (212 - 32) × 5/9\nC = 180 × 5/9\nC = 100\n\nTherefore, 212°",  # noqa: RUF001
            "role": "assistant",
            "completion_id": None,
            "sequence": 2,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "is_response": True,
        },
    ),
]


@pytest.fixture(scope="session", params=[pytest.param(True, id="streaming"), pytest.param(False, id="non-streaming")])
def response_streaming(request):
    return request.param


@pytest.fixture(scope="module")
def exercise_model(bedrock_converse_server, response_streaming):
    def _exercise_model(message):
        inference_config = {"temperature": 0.7, "maxTokens": 100}

        _response = bedrock_converse_server.converse(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            messages=message,
            system=[{"text": "You are a scientist."}],
            inferenceConfig=inference_config,
        )

    def _exercise_model_streaming(message):
        inference_config = {"temperature": 0.7, "maxTokens": 100}

        response = bedrock_converse_server.converse_stream(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            messages=message,
            system=[{"text": "You are a scientist."}],
            inferenceConfig=inference_config,
        )
        _responses = list(response["stream"])  # Consume the response stream
        pass

    return _exercise_model_streaming if response_streaming else _exercise_model


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_llm_metadata(set_trace_info, exercise_model):
    @validate_custom_events(events_with_context_attrs(chat_completion_expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=4)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_with_llm_metadata",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_in_txn_with_llm_metadata")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        with WithLlmCustomAttributes({"context": "attr"}):
            message = [{"role": "user", "content": [{"text": "What is 212 degrees Fahrenheit converted to Celsius?"}]}]
            exercise_model(message)

    _test()


@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
def test_bedrock_chat_completion_no_content(set_trace_info, exercise_model):
    @validate_custom_events(events_sans_content(chat_completion_expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=4)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_no_content",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_no_content")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        message = [{"role": "user", "content": [{"text": "What is 212 degrees Fahrenheit converted to Celsius?"}]}]
        exercise_model(message)

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_chat_completion_with_token_count(set_trace_info, exercise_model):
    @validate_custom_events(add_token_count_to_events(chat_completion_expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=4)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_with_token_count",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_with_token_count")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        message = [{"role": "user", "content": [{"text": "What is 212 degrees Fahrenheit converted to Celsius?"}]}]
        exercise_model(message)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_no_llm_metadata(set_trace_info, exercise_model):
    @validate_custom_events(events_sans_llm_metadata(chat_completion_expected_events))
    @validate_custom_event_count(count=4)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_no_llm_metadata",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_in_txn_no_llm_metadata")
    def _test():
        set_trace_info()
        message = [{"role": "user", "content": [{"text": "What is 212 degrees Fahrenheit converted to Celsius?"}]}]
        exercise_model(message)

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_bedrock_chat_completion_outside_txn(exercise_model):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    message = [{"role": "user", "content": [{"text": "What is 212 degrees Fahrenheit converted to Celsius?"}]}]
    exercise_model(message)


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task(name="test_bedrock_chat_completion_disabled_ai_monitoring_settings")
def test_bedrock_chat_completion_disabled_ai_monitoring_settings(set_trace_info, exercise_model):
    set_trace_info()
    message = [{"role": "user", "content": [{"text": "What is 212 degrees Fahrenheit converted to Celsius?"}]}]
    exercise_model(message)


chat_completion_invalid_access_key_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "span_id": None,
            "trace_id": "trace-id",
            "request_id": "e1206e19-2318-4a9d-be98-017c73f06118",
            "duration": None,  # Response time varies each test run
            "request.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "e1206e19-2318-4a9d-be98-017c73f06118",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "Invalid Token",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "response.model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]

_client_error = botocore.exceptions.ClientError
_client_error_name = callable_name(_client_error)


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_incorrect_access_key(
    monkeypatch, bedrock_converse_server, exercise_model, set_trace_info
):
    """
    A request is made to the server with invalid credentials. botocore will reach out to the server and receive an
    UnrecognizedClientException as a response. Information from the request will be parsed and reported in customer
    events. The error response can also be parsed, and will be included as attributes on the recorded exception.
    """

    @validate_custom_events(chat_completion_invalid_access_key_error_events)
    @validate_error_trace_attributes(
        _client_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "http.statusCode": 403,
                "error.message": "The security token included in the request is invalid.",
                "error.code": "UnrecognizedClientException",
            },
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        monkeypatch.setattr(bedrock_converse_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            message = [{"role": "user", "content": [{"text": "Invalid Token"}]}]

            response = bedrock_converse_server.converse(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                messages=message,
                inferenceConfig={"temperature": 0.7, "maxTokens": 100},
            )

            assert response

    _test()


chat_completion_invalid_model_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "request_id": "f4908827-3db9-4742-9103-2bbc34578b03",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "response.model": "does-not-exist",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "error": True,
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
            "request_id": "f4908827-3db9-4742-9103-2bbc34578b03",
            "content": "Model does not exist.",
            "role": "user",
            "completion_id": None,
            "response.model": "does-not-exist",
            "sequence": 0,
            "vendor": "bedrock",
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_invalid_model(bedrock_converse_server, set_trace_info):
    @validate_custom_events(events_with_context_attrs(chat_completion_invalid_model_error_events))
    @validate_error_trace_attributes(
        "botocore.errorfactory:ValidationException",
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "http.statusCode": 400,
                "error.message": "The provided model identifier is invalid.",
                "error.code": "ValidationException",
            },
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_error_invalid_model",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_error_invalid_model")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        with pytest.raises(_client_error):
            with WithLlmCustomAttributes({"context": "attr"}):
                message = [{"role": "user", "content": [{"text": "Model does not exist."}]}]

                response = bedrock_converse_server.converse(
                    modelId="does-not-exist", messages=message, inferenceConfig={"temperature": 0.7, "maxTokens": 100}
                )

                assert response

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_chat_completion_error_invalid_model_no_content(bedrock_converse_server, set_trace_info):
    @validate_custom_events(events_sans_content(chat_completion_invalid_model_error_events))
    @validate_error_trace_attributes(
        "botocore.errorfactory:ValidationException",
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "http.statusCode": 400,
                "error.message": "The provided model identifier is invalid.",
                "error.code": "ValidationException",
            },
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_error_invalid_model_no_content",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_error_invalid_model_no_content")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        with pytest.raises(_client_error):
            message = [{"role": "user", "content": [{"text": "Model does not exist."}]}]

            response = bedrock_converse_server.converse(
                modelId="does-not-exist", messages=message, inferenceConfig={"temperature": 0.7, "maxTokens": 100}
            )

            assert response

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_chat_completion_error_incorrect_access_key_with_token_count(
    monkeypatch, bedrock_converse_server, exercise_model, set_trace_info
):
    """
    A request is made to the server with invalid credentials. botocore will reach out to the server and receive an
    UnrecognizedClientException as a response. Information from the request will be parsed and reported in customer
    events. The error response can also be parsed, and will be included as attributes on the recorded exception.
    """

    @validate_custom_events(add_token_count_to_events(chat_completion_invalid_access_key_error_events))
    @validate_error_trace_attributes(
        _client_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "http.statusCode": 403,
                "error.message": "The security token included in the request is invalid.",
                "error.code": "UnrecognizedClientException",
            },
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_incorrect_access_key_with_token_count",
        scoped_metrics=[("Llm/completion/Bedrock/converse", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/converse", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_incorrect_access_key_with_token_count")
    def _test():
        monkeypatch.setattr(bedrock_converse_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            message = [{"role": "user", "content": [{"text": "Invalid Token"}]}]

            response = bedrock_converse_server.converse(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                messages=message,
                inferenceConfig={"temperature": 0.7, "maxTokens": 100},
            )

            assert response

    _test()
