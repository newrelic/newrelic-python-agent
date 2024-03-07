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
import pytest
from _test_bedrock_chat_completion import (
    chat_completion_expected_client_errors,
    chat_completion_expected_events,
    chat_completion_streaming_expected_events,
    chat_completion_invalid_access_key_error_events,
    chat_completion_payload_templates,
)
from conftest import disabled_ai_monitoring_settings  # pylint: disable=E0611
from conftest import BOTOCORE_VERSION
from testing_support.fixtures import (
    dt_enabled,
    override_application_settings,
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
def model_id(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=[
        "amazon.titan-text-express-v1",
        "anthropic.claude-instant-v1",
        "cohere.command-text-v14",
        "meta.llama2-13b-chat-v1",
    ],
)
def streaming_model_id(request):
    return request.param


@pytest.fixture(scope="module")
def exercise_model(bedrock_server, model_id, request_streaming):
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

    return _exercise_model


@pytest.fixture(scope="module")
def exercise_streaming_model(bedrock_server, streaming_model_id, request_streaming):
    payload_template = chat_completion_payload_templates[streaming_model_id]

    def _exercise_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % (prompt, temperature, max_tokens)).encode("utf-8")
        if request_streaming:
            body = BytesIO(body)

        response = bedrock_server.invoke_model_with_response_stream(
            body=body,
            modelId=streaming_model_id,
            accept="application/json",
            contentType="application/json",
        )
        body = response.get("body")
        for resp in body:
            assert resp

    return _exercise_model


@pytest.fixture(scope="module")
def expected_events(model_id):
    return chat_completion_expected_events[model_id]


@pytest.fixture(scope="module")
def streaming_expected_events(streaming_model_id):
    return chat_completion_streaming_expected_events[streaming_model_id]


@pytest.fixture(scope="module")
def expected_invalid_access_key_error_events(model_id):
    return chat_completion_invalid_access_key_error_events[model_id]


@pytest.fixture(scope="module")
def expected_events_no_convo_id(model_id):
    events = copy.deepcopy(chat_completion_expected_events[model_id])
    for event in events:
        event[1]["conversation_id"] = ""
    return events


@pytest.fixture(scope="module")
def expected_client_error(model_id):
    return chat_completion_expected_client_errors[model_id]


_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"


# not working with claude
@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_convo_id(set_trace_info, exercise_model, expected_events):
    @validate_custom_events(expected_events)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_with_convo_id",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_in_txn_with_convo_id")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_streaming_in_txn_with_convo_id(
    set_trace_info, exercise_streaming_model, streaming_expected_events
):
    @validate_custom_events(streaming_expected_events)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
       name="test_bedrock_chat_completion_streaming_in_txn_with_convo_id",
       scoped_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
       rollup_metrics=[("Llm/completion/Bedrock/invoke_model_with_response_stream", 1)],
       custom_metrics=[
           ("Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
       ],
       background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_chat_completion_streaming_in_txn_with_convo_id")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        exercise_streaming_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


# not working with claude
@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_no_convo_id(set_trace_info, exercise_model, expected_events_no_convo_id):
    @validate_custom_events(expected_events_no_convo_id)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_no_convo_id",
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_in_txn_no_convo_id")
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_bedrock_chat_completion_outside_txn(set_trace_info, exercise_model):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


disabled_custom_insights_settings = {"custom_insights_events.enabled": False}


@override_application_settings(disabled_custom_insights_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_bedrock_chat_completion_disabled_custom_events_settings",
    custom_metrics=[
        ("Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
    ],
    background_task=True,
)
@background_task(name="test_bedrock_chat_completion_disabled_custom_events_settings")
def test_bedrock_chat_completion_disabled_custom_events_settings(set_trace_info, exercise_model):
    set_trace_info()
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


chat_completion_invalid_model_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (external_botocore)",
            "transaction_id": "transaction-id",
            "conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "api_key_last_four_digits": "CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "response.model": "does-not-exist",
            "request_id": "",
            "vendor": "bedrock",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]


@reset_core_stats_engine()
def test_bedrock_chat_completion_error_invalid_model(bedrock_server, set_trace_info):
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
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_error_invalid_model")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with pytest.raises(_client_error):
            bedrock_server.invoke_model(
                body=b"{}",
                modelId="does-not-exist",
                accept="application/json",
                contentType="application/json",
            )

    _test()


@dt_enabled
@reset_core_stats_engine()
def test_bedrock_chat_completion_error_incorrect_access_key(
    monkeypatch,
    bedrock_server,
    exercise_model,
    set_trace_info,
    expected_client_error,
    expected_invalid_access_key_error_events,
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
        scoped_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/completion/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


def test_bedrock_chat_completion_functions_marked_as_wrapped_for_sdk_compatibility(bedrock_server):
    assert bedrock_server._nr_wrapped
