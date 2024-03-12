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
import json
from io import BytesIO

import botocore.errorfactory
import botocore.exceptions
import botocore.eventstream

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
from conftest import (  # pylint: disable=E0611
    BOTOCORE_VERSION,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
)
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_attributes,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import function_wrapper


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
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(response.get("body").read())
        assert response_body

        return response_body

    def _exercise_streaming_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % (prompt, temperature, max_tokens)).encode("utf-8")
        if request_streaming:
            body = BytesIO(body)

        response = bedrock_server.invoke_model_with_response_stream(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
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
def expected_events_no_content(expected_events):
    events = copy.deepcopy(expected_events)
    for event in events:
        if "content" in event[1]:
            del event[1]["content"]
    return events


@pytest.fixture(scope="module")
def expected_invalid_access_key_error_events(model_id):
    return chat_completion_invalid_access_key_error_events[model_id]


@pytest.fixture(scope="module")
def expected_events_no_llm_metadata(expected_events):
    events = copy.deepcopy(expected_events)
    for event in events:
        del event[1]["llm.conversation_id"], event[1]["llm.foo"]
    return events


@pytest.fixture(scope="module")
def expected_invalid_access_key_error_events_no_content(expected_invalid_access_key_error_events):
    events = copy.deepcopy(expected_invalid_access_key_error_events)
    for event in events:
        if "content" in event[1]:
            del event[1]["content"]
    return events


_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"


# not working with claude
@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_llm_metadata(set_trace_info, exercise_model, expected_events, expected_metrics):
    @validate_custom_events(expected_events)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_with_llm_metadata",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_in_txn_with_llm_metadata")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_llm_metadata_no_content(
    set_trace_info, exercise_model, expected_events_no_content, expected_metrics
):
    @validate_custom_events(expected_events_no_content)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_with_llm_metadata_no_content",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_in_txn_with_llm_metadata_no_content")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_no_llm_metadata(set_trace_info, exercise_model, expected_events_no_llm_metadata, expected_metrics):
    @validate_custom_events(expected_events_no_llm_metadata)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_no_llm_metadata",
        scoped_metrics=expected_metrics,
        rollup_metrics=expected_metrics,
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_in_txn_no_llm_metadata")
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_bedrock_chat_completion_outside_txn(set_trace_info, exercise_model):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task(name="test_bedrock_chat_completion_disabled_ai_monitoring_setting")
def test_bedrock_chat_completion_disabled_ai_monitoring_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


_client_error = botocore.exceptions.ClientError
_client_error_name = callable_name(_client_error)


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_invalid_model(bedrock_server, set_trace_info, response_streaming, expected_metrics):
    @validate_custom_events(chat_completion_invalid_model_error_events)
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
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_error_invalid_model")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        with pytest.raises(_client_error):
            if response_streaming:
                stream = bedrock_server.invoke_model_with_response_stream(
                    body=b"{}",
                    modelId="does-not-exist",
                    accept="application/json",
                    contentType="application/json",
                )
                for _ in stream: pass
            else:
                bedrock_server.invoke_model(
                    body=b"{}",
                    modelId="does-not-exist",
                    accept="application/json",
                    contentType="application/json",
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
    For both streaming or non-streaming, request has invalid credentials.

    * Library will reach out to server and receive a UnrecognizedClientException as a response.
    * Request and response can both be parsed, so request information and error attributes from response are available.
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
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
    expected_invalid_access_key_error_events_no_content,
    expected_metrics,
):
    """
    Duplicate of the above test, but with content recording is disabled.

    For both streaming or non-streaming, request has invalid credentials.

    * Library will reach out to server and receive a UnrecognizedClientException as a response.
    * Request and response can both be parsed, so request information and error attributes from response are available.
    * The contents of all messages will not be included in events.
    """

    @validate_custom_events(expected_invalid_access_key_error_events_no_content)
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
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
def test_bedrock_chat_completion_error_malformed_request_body(
    bedrock_server,
    set_trace_info,
    response_streaming,
    expected_metrics,
):
    """
    For both streaming or non-streaming, request body contains invalid JSON.

    * Library will still reach out to server and receive a ValidationException as a response.
    * Request cannot be parsed, so no request information will be added.
    * Response payload can be parsed, so error attributes from response will appear as normal.
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
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
                    body=body,
                    modelId=model,
                    accept="application/json",
                    contentType="application/json",
                )
            else:
                bedrock_server.invoke_model(
                    body=body,
                    modelId=model,
                    accept="application/json",
                    contentType="application/json",
                )

    _test()



@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_response_body(
    bedrock_server,
    set_trace_info,
):
    """
    After a non-streaming call, the response body contains invalid JSON.

    * No actual error should be raised by the library or our code.
    * An invalid payload is returned by the library to the user.
    * No response can be parsed, meaning all response data should be missing.
    """

    @validate_custom_events(chat_completion_expected_malformed_response_body_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
            body=body,
            modelId=model,
            accept="application/json",
            contentType="application/json",
        )
        assert response

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_response_streaming_body(
    bedrock_server,
    set_trace_info,
):
    """
    After a streaming call, the chunk returned by the server is valid, but contains a body with JSON that cannot be parsed.

    * No actual error should be raised by the library or our code.
    * An invalid payload is returned by the library to the user.
    * No response can be parsed, meaning all response data should be missing.
    """

    @validate_custom_events(chat_completion_expected_malformed_response_streaming_body_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
            body=body,
            modelId=model,
            accept="application/json",
            contentType="application/json",
        )
        
        chunks = list(response["body"])
        assert chunks, "No response chunks returned"
        for chunk in chunks:
            with pytest.raises(json.decoder.JSONDecodeError):
                json.loads(chunk["chunk"]["bytes"])

    _test()


_headers_error = botocore.eventstream.InvalidHeadersLength
_headers_error_name = "botocore.eventstream:InvalidHeadersLength"

@reset_core_stats_engine()
def test_bedrock_chat_completion_error_malformed_response_streaming_chunk(
    bedrock_server,
    set_trace_info,
):
    """
    After a streaming call, the chunk returned by the server is invalid and cannot be parsed.

    * The library should throw an appropriate error, in this case InvalidHeadersLength.
    * The thrown error will not include a response attribute as the response was invalid.
    * No response can be parsed, meaning all response data should be missing.
    """
    
    @validate_custom_events(chat_completion_expected_malformed_response_streaming_chunk_events)
    @validate_custom_event_count(count=2)
    @validate_error_trace_attributes(
        _headers_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": {
                'llm.conversation_id': 'my-awesome-id',
            },
        },
        forgone_params={
            "agent": (),
            "intrinsic": (),
            "user": ("http.statusCode", "error.message", "error.code"),
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        model = "amazon.titan-text-express-v1"
        body = (chat_completion_payload_templates[model] % ("Malformed Streaming Chunk", 0.7, 100)).encode("utf-8")
        with pytest.raises(_headers_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            response = bedrock_server.invoke_model_with_response_stream(
                body=body,
                modelId=model,
                accept="application/json",
                contentType="application/json",
            )
            response = "".join(chunk for chunk in response["body"])
            assert response

    _test()


_event_stream_error = botocore.exceptions.EventStreamError
_event_stream_error_name = "botocore.exceptions:EventStreamError"


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_streaming_exception(
    bedrock_server,
    set_trace_info,
):
    """
    During a streaming call, the chunk's headers indicate an exception.

    * The library converts this into an actual exception and raises it.
    * The response attribute on the exception will contain only the error information.
    * The parsed response will include exception attributes but no response message.
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
        forgone_params={
            "agent": (),
            "intrinsic": (),
            "user": ("http.statusCode"),
        }
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
                body=body,
                modelId=model,
                accept="application/json",
                contentType="application/json",
            )
            list(response["body"])  # Iterate

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_chat_completion_error_streaming_exception_no_content(
    bedrock_server,
    set_trace_info,
):
    """
    Duplicate of the above test, but with content recording is disabled.

    During a streaming call, the chunk's headers indicate an exception.

    * The library converts this into an actual exception and raises it.
    * The response attribute on the exception will contain only the error information.
    * The parsed response will include exception attributes as normal.
    * The contents of all messages will not be included in events.
    """
    chat_completion_expected_streaming_error_events_no_content = copy.deepcopy(chat_completion_expected_streaming_error_events)
    del chat_completion_expected_streaming_error_events_no_content[1][1]["content"]

    @validate_custom_events(chat_completion_expected_streaming_error_events_no_content)
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
        forgone_params={
            "agent": (),
            "intrinsic": (),
            "user": ("http.statusCode"),
        }
    )
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
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
                body=body,
                modelId=model,
                accept="application/json",
                contentType="application/json",
            )
            list(response["body"])  # Iterate

    _test()


def test_bedrock_chat_completion_functions_marked_as_wrapped_for_sdk_compatibility(bedrock_server):
    assert bedrock_server._nr_wrapped
