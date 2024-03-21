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
from io import BytesIO

import botocore.exceptions
import pytest
from _test_bedrock_embeddings import (
    embedding_expected_client_errors,
    embedding_expected_error_events,
    embedding_expected_events,
    embedding_payload_templates,
)
from conftest import (  # pylint: disable=E0611
    BOTOCORE_VERSION,
)
from testing_support.fixtures import (
    dt_enabled,
    reset_core_stats_engine,
    validate_attributes,
    validate_custom_event_count,
    override_llm_token_callback_settings,
)
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
    events_sans_content,
    llm_token_count_callback,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    set_trace_info,
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
        "amazon.titan-embed-text-v1",
        "amazon.titan-embed-g1-text-02",
    ],
)
def model_id(request):
    return request.param


@pytest.fixture(scope="module")
def exercise_model(bedrock_server, model_id, request_streaming):
    payload_template = embedding_payload_templates[model_id]

    def _exercise_model(prompt):
        body = (payload_template % prompt).encode("utf-8")
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
def expected_events(model_id):
    return embedding_expected_events[model_id]


@pytest.fixture(scope="module")
def expected_error_events(model_id):
    return embedding_expected_error_events[model_id]


@pytest.fixture(scope="module")
def expected_client_error(model_id):
    return embedding_expected_client_errors[model_id]

  
@pytest.fixture(scope="module")
def expected_invalid_access_key_error_events(model_id):
    return embedding_invalid_access_key_error_events[model_id]


@reset_core_stats_engine()
def test_bedrock_embedding_in_txn_with_llm_metadata(set_trace_info, exercise_model, expected_events):
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=1)
    @validate_transaction_metrics(
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_embedding")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        exercise_model(prompt=_test_bedrock_embedding_prompt)

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_embedding_no_content(set_trace_info, exercise_model, model_id):
    @validate_custom_events(events_sans_content(embedding_expected_events[model_id]))
    @validate_custom_event_count(count=1)
    @validate_transaction_metrics(
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_embedding")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")
        exercise_model(prompt=_test_bedrock_embedding_prompt)

    _test()


@reset_core_stats_engine()
def test_bedrock_embedding_in_txn_no_llm_metadata(set_trace_info, exercise_model, expected_events_no_llm_metadata):
    @validate_custom_events(expected_events_no_llm_metadata)
    @validate_custom_event_count(count=1)
    @validate_transaction_metrics(
        name="test_bedrock_embedding_in_txn_no_llm_metadata",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_embedding_in_txn_no_llm_metadata")
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_embedding_prompt)

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_embedding_with_token_count(set_trace_info, exercise_model, expected_events):
    @validate_custom_events(add_token_count_to_events(expected_events))
    @validate_custom_event_count(count=1)
    @validate_transaction_metrics(
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @validate_attributes("agent", ["llm"])
    @background_task(name="test_bedrock_embedding")
    def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        exercise_model(prompt="This is an embedding test.")

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_bedrock_embedding_outside_txn(exercise_model):
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_embedding_prompt)


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task(name="test_bedrock_embedding_disabled_ai_monitoring_setting")
def test_bedrock_embedding_disabled_ai_monitoring_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt=_test_bedrock_embedding_prompt)


_client_error = botocore.exceptions.ClientError
_client_error_name = callable_name(_client_error)


@reset_core_stats_engine()
def test_bedrock_embedding_error_incorrect_access_key(
    monkeypatch,
    bedrock_server,
    exercise_model,
    set_trace_info,
    
  ,
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
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_embedding")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token")

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_embedding_error_incorrect_access_key_no_content(
    monkeypatch, bedrock_server, exercise_model, set_trace_info, model_id, expected_client_error
):
    @validate_custom_events(events_sans_content(embedding_expected_error_events[model_id]))
    @validate_error_trace_attributes(
        _client_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": expected_client_error,
        },
    )
    @validate_transaction_metrics(
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_embedding")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token")

    _test()


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
def test_bedrock_embedding_error_incorrect_access_key_with_token_count(
    monkeypatch,
    bedrock_server,
    exercise_model,
    set_trace_info,
    expected_invalid_access_key_error_events,
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
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        background_task=True,
    )
    @background_task(name="test_bedrock_embedding")
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            add_custom_attribute("llm.conversation_id", "my-awesome-id")
            add_custom_attribute("llm.foo", "bar")
            add_custom_attribute("non_llm_attr", "python-agent")

            exercise_model(prompt="Invalid Token")

    _test()


@reset_core_stats_engine()
def test_bedrock_embedding_error_malformed_request_body(
    bedrock_server,
    set_trace_info,
):
    """
    A request was made to the server, but the request body contains invalid JSON. The library will accept the invalid
    payload, and still send a request. Our instrumentation will be unable to read it. As a result, no request
    information will be recorded in custom events. This includes the initial prompt message event, which cannot be read
    so it cannot be captured. The server will then respond with a ValidationException response immediately due to the
    bad request. The response can still be parsed, so error information from the response will be recorded as normal.
    """

    @validate_custom_events(embedding_expected_malformed_request_body_events)
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
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_embedding")
    def _test():
        model = "amazon.titan-embed-g1-text-02"
        body = "{ Malformed Request Body".encode("utf-8")
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        with pytest.raises(_client_error):
            bedrock_server.invoke_model(
                body=body,
                modelId=model,
                accept="application/json",
                contentType="application/json",
            )

    _test()


@reset_core_stats_engine()
def test_bedrock_embedding_error_malformed_response_body(
    bedrock_server,
    set_trace_info,
):
    """
    After a non-streaming request was made to the server, the server responded with a response body that contains
    invalid JSON. Since the JSON body is not parsed by botocore and just returned to the user as bytes, no parsing
    exceptions will be raised. Instrumentation will attempt to parse the invalid body, and should not raise an
    exception when it fails to do so. As a result, recorded events will not contain the streamed response data but will contain the request data.
    """

    @validate_custom_events(embedding_expected_malformed_response_body_events)
    @validate_custom_event_count(count=1)
    @validate_transaction_metrics(
        name="test_bedrock_embedding",
        scoped_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        rollup_metrics=[("Llm/embedding/Bedrock/invoke_model", 1)],
        custom_metrics=[
            ("Supportability/Python/ML/Bedrock/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_embedding")
    def _test():
        model = "amazon.titan-embed-g1-text-02"
        body = (embedding_payload_templates[model] % "Malformed Body").encode("utf-8")
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
