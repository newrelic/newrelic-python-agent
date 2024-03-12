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

import botocore.exceptions
import botocore.eventstream

import pytest
from _test_bedrock_chat_completion import (
    chat_completion_expected_client_errors,
    chat_completion_expected_events,
    chat_completion_invalid_access_key_error_events,
    chat_completion_invalid_model_error_events,
    chat_completion_expected_malformed_payload_events,
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


@pytest.fixture(scope="module")
def expected_client_error(model_id):
    return chat_completion_expected_client_errors[model_id]


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
    expected_client_error,
    expected_invalid_access_key_error_events,
    expected_metrics,
):
    @validate_custom_events(expected_invalid_access_key_error_events)
    @validate_error_trace_attributes(
        _client_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": expected_client_error,
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

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
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
    expected_client_error,
    expected_invalid_access_key_error_events_no_content,
    expected_metrics,
):
    @validate_custom_events(expected_invalid_access_key_error_events_no_content)
    @validate_error_trace_attributes(
        _client_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": expected_client_error,
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

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_malformed_payload(
    bedrock_server,
    set_trace_info,
):
    # No actual error should be raised, an invalid payload is returned
    @validate_custom_events(chat_completion_expected_malformed_payload_events)
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
        body = (chat_completion_payload_templates[model] % ("Malformed Payload", 0.7, 100)).encode("utf-8")
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



def test_bedrock_chat_completion_functions_marked_as_wrapped_for_sdk_compatibility(bedrock_server):
    assert bedrock_server._nr_wrapped
