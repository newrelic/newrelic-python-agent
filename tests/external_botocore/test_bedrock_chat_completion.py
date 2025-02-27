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
import json
import os
from io import BytesIO

import boto3
import botocore.errorfactory
import botocore.eventstream
import botocore.exceptions
import pytest
from _test_bedrock_chat_completion import (
    chat_completion_expected_events,
    chat_completion_expected_malformed_request_body_events,
    chat_completion_expected_malformed_response_body_events,
    chat_completion_expected_malformed_response_streaming_body_events,
    chat_completion_expected_malformed_response_streaming_chunk_events,
    chat_completion_expected_streaming_error_events,
    chat_completion_invalid_access_key_error_events,
    chat_completion_invalid_model_error_events,
    chat_completion_payload_templates,
    chat_completion_streaming_expected_events,
)
from conftest import BOTOCORE_VERSION  # pylint: disable=E0611
from testing_support.fixtures import override_llm_token_callback_settings, reset_core_stats_engine, validate_attributes
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
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name
from newrelic.hooks.external_botocore import MODEL_EXTRACTORS


@pytest.fixture(scope="session", params=[False, True], ids=["ResponseStandard", "ResponseStreaming"])
def response_streaming(request):
    return request.param


@pytest.fixture(scope="session", params=[False, True], ids=["RequestStandard", "RequestStreaming"])
def request_streaming(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=[
        "amazon.titan-text-express-v1",
        "ai21.j2-mid-v1",
        "anthropic.claude-instant-v1",
        "cohere.command-text-v14",
        "meta.llama2-13b-chat-v1",
        "mistral.mistral-7b-instruct-v0:2",
    ],
)
def model_id(request, response_streaming):
    model = request.param
    if response_streaming and model == "ai21.j2-mid-v1":
        pytest.skip(reason="Streaming not supported.")

    return model


@pytest.fixture(scope="module")
def exercise_model(bedrock_server, model_id, request_streaming, response_streaming):
    payload_template = chat_completion_payload_templates[model_id]

    def _exercise_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % (prompt, temperature, max_tokens)).encode("utf-8")
        if request_streaming:
            body = BytesIO(body)

        response = bedrock_server.invoke_model(
            body=body, modelId=model_id, accept="application/json", contentType="application/json"
        )
        response_body = json.loads(response.get("body").read())
        assert response_body

        return response_body

    def _exercise_streaming_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % (prompt, temperature, max_tokens)).encode("utf-8")
        if request_streaming:
            body = BytesIO(body)

        response = bedrock_server.invoke_model_with_response_stream(
            body=body, modelId=model_id, accept="application/json", contentType="application/json"
        )
        body = response.get("body")
        for resp in body:
            assert resp

    if response_streaming:
        return _exercise_streaming_model
    else:
        return _exercise_model


@pytest.fixture(scope="module")
def expected_events(model_id, response_streaming):
    if response_streaming:
        return chat_completion_streaming_expected_events[model_id]
    else:
        return chat_completion_expected_events[model_id]


@pytest.fixture(scope="module")
def expected_metrics(response_streaming):
    if response_streaming:
        return [("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)]
    else:
        return [("Llm/completion/Bedrock/invoke_model", 1)]


@pytest.fixture(scope="module")
def expected_invalid_access_key_error_events(model_id):
    return chat_completion_invalid_access_key_error_events[model_id]


_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_llm_metadata(
    set_trace_info, exercise_model, expected_events, expected_metrics
):
    @validate_custom_events(events_with_context_attrs(expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_with_llm_metadata",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
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
            exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
def test_bedrock_chat_completion_no_content(set_trace_info, exercise_model, expected_events, expected_metrics):
    @validate_custom_events(events_sans_content(expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_no_content",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
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
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_chat_completion_with_token_count(set_trace_info, exercise_model, expected_events, expected_metrics):
    @validate_custom_events(add_token_count_to_events(expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_with_token_count",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
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
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_no_llm_metadata(set_trace_info, exercise_model, expected_events, expected_metrics):
    @validate_custom_events(events_sans_llm_metadata(expected_events))
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_no_llm_metadata",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_in_txn_no_llm_metadata")
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_bedrock_chat_completion_outside_txn(exercise_model):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task(name="test_bedrock_chat_completion_disabled_ai_monitoring_setting")
def test_bedrock_chat_completion_disabled_ai_monitoring_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


@reset_core_stats_engine()
@disabled_ai_monitoring_streaming_settings
def test_bedrock_chat_completion_streaming_disabled(bedrock_server):
    """Streaming is disabled, but the rest of the AI settings are enabled. Custom events should not be collected."""

    @validate_custom_event_count(count=0)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        model = "amazon.titan-text-express-v1"
        body = (chat_completion_payload_templates[model] % (_test_bedrock_chat_completion_prompt, 0.7, 100)).encode(
            "utf-8"
        )

        response = bedrock_server.invoke_model_with_response_stream(
            body=body, modelId=model, accept="application/json", contentType="application/json"
        )
        list(response["body"])  # Iterate

    _test()


_client_error = botocore.exceptions.ClientError
_client_error_name = callable_name(_client_error)


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_invalid_model(
    bedrock_server, set_trace_info, response_streaming, expected_metrics
):
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
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
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
                if response_streaming:
                    stream = bedrock_server.invoke_model_with_response_stream(
                        body=b"{}", modelId="does-not-exist", accept="application/json", contentType="application/json"
                    )
                    for _ in stream:
                        pass
                else:
                    bedrock_server.invoke_model(
                        body=b"{}", modelId="does-not-exist", accept="application/json", contentType="application/json"
                    )

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_incorrect_access_key(
    monkeypatch,
    bedrock_server,
    exercise_model,
    set_trace_info,
    expected_invalid_access_key_error_events,
    expected_metrics,
):
    """
    A request is made to the server with invalid credentials. botocore will reach out to the server and receive an
    UnrecognizedClientException as a response. Information from the request will be parsed and reported in customer
    events. The error response can also be parsed, and will be included as attributes on the recorded exception.
    """

    @validate_custom_events(expected_invalid_access_key_error_events)
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
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_chat_completion_error_incorrect_access_key_no_content(
    monkeypatch,
    bedrock_server,
    exercise_model,
    set_trace_info,
    expected_invalid_access_key_error_events,
    expected_metrics,
):
    """
    Duplicate of test_bedrock_chat_completion_error_incorrect_access_key, but with content recording disabled.

    See the original test for a description of the error case.
    """

    @validate_custom_events(events_sans_content(expected_invalid_access_key_error_events))
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
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_chat_completion_error_incorrect_access_key_with_token(
    monkeypatch,
    bedrock_server,
    exercise_model,
    set_trace_info,
    expected_invalid_access_key_error_events,
    expected_metrics,
):
    @validate_custom_events(add_token_count_to_events(expected_invalid_access_key_error_events))
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
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_request_body(
    bedrock_server, set_trace_info, response_streaming, expected_metrics
):
    """
    A request was made to the server, but the request body contains invalid JSON. The library will accept the invalid
    payload, and still send a request. Our instrumentation will be unable to read it. As a result, no request
    information will be recorded in custom events. This includes the initial prompt message event, which cannot be read
    so it cannot be captured. The server will then respond with a ValidationException response immediately due to the
    bad request. The response can still be parsed, so error information from the response will be recorded as normal.
    """

    @validate_custom_events(chat_completion_expected_malformed_request_body_events)
    @validate_custom_event_count(count=1)
    @validate_error_trace_attributes(
        "botocore.errorfactory:ValidationException",
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "http.statusCode": 400,
                "error.message": "Malformed input request, please reformat your input and try again.",
                "error.code": "ValidationException",
            },
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        model = "amazon.titan-text-express-v1"
        body = "{ Malformed Request Body".encode("utf-8")
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        with pytest.raises(_client_error):
            if response_streaming:
                bedrock_server.invoke_model_with_response_stream(
                    body=body, modelId=model, accept="application/json", contentType="application/json"
                )
            else:
                bedrock_server.invoke_model(
                    body=body, modelId=model, accept="application/json", contentType="application/json"
                )

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_response_body(bedrock_server, set_trace_info):
    """
    After a non-streaming request was made to the server, the server responded with a response body that contains
    invalid JSON. Since the JSON body is not parsed by botocore and just returned to the user as bytes, no parsing
    exceptions will be raised. Instrumentation will attempt to parse the invalid body, and should not raise an
    exception when it fails to do so. As a result, recorded events will not contain the streamed response data but will contain the request data.
    """

    @validate_custom_events(chat_completion_expected_malformed_response_body_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        model = "amazon.titan-text-express-v1"
        body = (chat_completion_payload_templates[model] % ("Malformed Body", 0.7, 100)).encode("utf-8")
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        response = bedrock_server.invoke_model(
            body=body, modelId=model, accept="application/json", contentType="application/json"
        )
        assert response

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_response_streaming_body(bedrock_server, set_trace_info):
    """
    A chunk in the stream returned by the server is valid, but contains a body with JSON that cannot be parsed.
    Since the JSON body is not parsed by botocore and just returned to the user as bytes, no parsing exceptions will
    be raised. Instrumentation will attempt to parse the invalid body, and should not raise an exception when it fails
    to do so. The result should be all streamed response data missing from the recorded events, but request and summary
    events are recorded as normal.
    """

    @validate_custom_events(chat_completion_expected_malformed_response_streaming_body_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        model = "amazon.titan-text-express-v1"
        body = (chat_completion_payload_templates[model] % ("Malformed Streaming Body", 0.7, 100)).encode("utf-8")

        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        response = bedrock_server.invoke_model_with_response_stream(
            body=body, modelId=model, accept="application/json", contentType="application/json"
        )

        chunks = list(response["body"])
        assert chunks, "No response chunks returned"
        for chunk in chunks:
            with pytest.raises(json.decoder.JSONDecodeError):
                json.loads(chunk["chunk"]["bytes"])

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_response_streaming_chunk(bedrock_server, set_trace_info):
    """
    A chunk in the stream returned by the server is missing the prelude which causes an InvalidHeadersLength exception
    to be raised during parsing of the chunk. Since the streamed chunk is not able to be parsed, the response
    attribute on the raised exception is not present. This means all streamed response data will be missing from the
    recorded events.
    """

    @validate_custom_events(chat_completion_expected_malformed_response_streaming_chunk_events)
    @validate_custom_event_count(count=2)
    @validate_error_trace_attributes(
        "botocore.eventstream:ChecksumMismatch",
        exact_attrs={"agent": {}, "intrinsic": {}, "user": {"llm.conversation_id": "my-awesome-id"}},
        forgone_params={"agent": (), "intrinsic": (), "user": ("http.statusCode", "error.message", "error.code")},
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        model = "amazon.titan-text-express-v1"
        body = (chat_completion_payload_templates[model] % ("Malformed Streaming Chunk", 0.7, 100)).encode("utf-8")
        with pytest.raises(botocore.eventstream.ChecksumMismatch):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            response = bedrock_server.invoke_model_with_response_stream(
                body=body, modelId=model, accept="application/json", contentType="application/json"
            )
            response = "".join(chunk for chunk in response["body"])
            assert response

    _test()


_event_stream_error = botocore.exceptions.EventStreamError
_event_stream_error_name = "botocore.exceptions:EventStreamError"


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_streaming_exception(bedrock_server, set_trace_info):
    """
    During a streaming call, the streamed chunk's headers indicate an error. These headers are not HTTP headers, but
    headers embedded in the binary format of the response from the server. The streamed chunk's response body is not
    required to contain any information regarding the exception, the headers are sufficient to cause botocore's
    parser to raise an actual exception based on the error code. The response attribute on the raised exception will
    contain the error information. This means error data will be reported for the response, but all response message
    data will be missing from the recorded events since the server returned an error instead of message data inside
    the streamed response.
    """

    @validate_custom_events(chat_completion_expected_streaming_error_events)
    @validate_custom_event_count(count=2)
    @validate_error_trace_attributes(
        _event_stream_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "error.message": "Malformed input request, please reformat your input and try again.",
                "error.code": "ValidationException",
            },
        },
        forgone_params={"agent": (), "intrinsic": (), "user": ("http.statusCode")},
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        with pytest.raises(_event_stream_error):
            model = "amazon.titan-text-express-v1"
            body = (chat_completion_payload_templates[model] % ("Streaming Exception", 0.7, 100)).encode("utf-8")

            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            response = bedrock_server.invoke_model_with_response_stream(
                body=body, modelId=model, accept="application/json", contentType="application/json"
            )
            list(response["body"])  # Iterate

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_chat_completion_error_streaming_exception_no_content(bedrock_server, set_trace_info):
    """
    Duplicate of test_bedrock_chat_completion_error_streaming_exception, but with content recording disabled.

    See the original test for a description of the error case.
    """

    @validate_custom_events(events_sans_content(chat_completion_expected_streaming_error_events))
    @validate_custom_event_count(count=2)
    @validate_error_trace_attributes(
        _event_stream_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "error.message": "Malformed input request, please reformat your input and try again.",
                "error.code": "ValidationException",
            },
        },
        forgone_params={"agent": (), "intrinsic": (), "user": ("http.statusCode")},
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        with pytest.raises(_event_stream_error):
            model = "amazon.titan-text-express-v1"
            body = (chat_completion_payload_templates[model] % ("Streaming Exception", 0.7, 100)).encode("utf-8")

            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            response = bedrock_server.invoke_model_with_response_stream(
                body=body, modelId=model, accept="application/json", contentType="application/json"
            )
            list(response["body"])  # Iterate

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_chat_completion_error_streaming_exception_with_token_count(bedrock_server, set_trace_info):
    """
    Duplicate of test_bedrock_chat_completion_error_streaming_exception, but with token callback being set.

    See the original test for a description of the error case.
    """

    @validate_custom_events(add_token_count_to_events(chat_completion_expected_streaming_error_events))
    @validate_custom_event_count(count=2)
    @validate_error_trace_attributes(
        _event_stream_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                "error.message": "Malformed input request, please reformat your input and try again.",
                "error.code": "ValidationException",
            },
        },
        forgone_params={"agent": (), "intrinsic": (), "user": ("http.statusCode")},
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[(f"Supportability/Python/ML/Bedrock/{BOTOCORE_VERSION}", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        with pytest.raises(_event_stream_error):
            model = "amazon.titan-text-express-v1"
            body = (chat_completion_payload_templates[model] % ("Streaming Exception", 0.7, 100)).encode("utf-8")

            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            response = bedrock_server.invoke_model_with_response_stream(
                body=body, modelId=model, accept="application/json", contentType="application/json"
            )
            list(response["body"])  # Iterate

    _test()


def test_bedrock_chat_completion_functions_marked_as_wrapped_for_sdk_compatibility(bedrock_server):
    assert bedrock_server._nr_wrapped


def test_chat_models_instrumented():
    SUPPORTED_MODELS = [model for model, _, _, _ in MODEL_EXTRACTORS if "embed" not in model]

    _id = os.environ.get("AWS_ACCESS_KEY_ID")
    key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not _id or not key:
        pytest.skip(reason="Credentials not available.")

    client = boto3.client("bedrock", "us-east-1")
    response = client.list_foundation_models(byOutputModality="TEXT")
    models = [model["modelId"] for model in response["modelSummaries"]]
    not_supported = []
    for model in models:
        is_supported = any([model.startswith(supported_model) for supported_model in SUPPORTED_MODELS])
        if not is_supported:
            not_supported.append(model)

    assert not not_supported, f"The following unsupported models were found: {not_supported}"
