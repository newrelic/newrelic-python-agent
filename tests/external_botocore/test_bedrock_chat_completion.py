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
    chat_completion_payload_templates,
)
from conftest import BOTOCORE_VERSION
from testing_support.fixtures import (
    dt_enabled,
    override_application_settings,
    reset_core_stats_engine,
    validate_custom_event_count,
)
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name


@pytest.fixture(scope="session", params=[False, True], ids=["Bytes", "Stream"])
def is_file_payload(request):
    return request.param


@pytest.fixture(
    scope="module",
    params=[
        "amazon.titan-text-express-v1",
        "ai21.j2-mid-v1",
        "anthropic.claude-instant-v1",
        "cohere.command-text-v14",
    ],
)
def model_id(request):
    return request.param


@pytest.fixture(scope="module")
def exercise_model(bedrock_server, model_id, is_file_payload):
    payload_template = chat_completion_payload_templates[model_id]

    def _exercise_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % (prompt, temperature, max_tokens)).encode("utf-8")
        if is_file_payload:
            body = BytesIO(body)

        response = bedrock_server.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(response.get("body").read())
        assert response_body

    return _exercise_model


@pytest.fixture(scope="module")
def expected_events(model_id):
    return chat_completion_expected_events[model_id]


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
        custom_metrics=[
            ("Python/ML/Botocore/%s" % BOTOCORE_VERSION, 1),
        ],
        background_task=True,
    )
    @background_task(name="test_bedrock_chat_completion_in_txn_with_convo_id")
    def _test():
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


# not working with claude
@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_no_convo_id(set_trace_info, exercise_model, expected_events_no_convo_id):
    @validate_custom_events(expected_events_no_convo_id)
    # One summary event, one user message, and one response message from the assistant
    @validate_custom_event_count(count=3)
    @validate_transaction_metrics(
        name="test_bedrock_chat_completion_in_txn_no_convo_id",
        custom_metrics=[
            ("Python/ML/Botocore/%s" % BOTOCORE_VERSION, 1),
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
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


disabled_ml_settings = {"machine_learning.enabled": False, "ml_insights_events.enabled": False}


@override_application_settings(disabled_ml_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_bedrock_chat_completion_disabled_settings",
    custom_metrics=[
        ("Python/ML/Botocore/%s" % BOTOCORE_VERSION, 1),
    ],
    background_task=True,
)
@background_task(name="test_bedrock_chat_completion_disabled_settings")
def test_bedrock_chat_completion_disabled_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


_client_error = botocore.exceptions.ClientError
_client_error_name = callable_name(_client_error)


@validate_error_trace_attributes(
    "botocore.errorfactory:ValidationException",
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "conversation_id": "my-awesome-id",
            "request_id": "f4908827-3db9-4742-9103-2bbc34578b03",
            "api_key_last_four_digits": "CRET",
            "request.model": "does-not-exist",
            "vendor": "Bedrock",
            "ingest_source": "Python",
            "http.statusCode": 400,
            "error.message": "The provided model identifier is invalid.",
            "error.code": "ValidationException",
        },
    },
)
@background_task()
def test_bedrock_chat_completion_error_invalid_model(bedrock_server, set_trace_info):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    with pytest.raises(_client_error):
        bedrock_server.invoke_model(
            body=b"{}",
            modelId="does-not-exist",
            accept="application/json",
            contentType="application/json",
        )


@dt_enabled
@reset_core_stats_engine()
def test_bedrock_chat_completion_error_incorrect_access_key(
    monkeypatch, bedrock_server, exercise_model, set_trace_info, expected_client_error
):
    @validate_error_trace_attributes(
        _client_error_name,
        exact_attrs={
            "agent": {},
            "intrinsic": {},
            "user": expected_client_error,
        },
    )
    @background_task()
    def _test():
        monkeypatch.setattr(bedrock_server._request_signer._credentials, "access_key", "INVALID-ACCESS-KEY")

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            add_custom_attribute("conversation_id", "my-awesome-id")
            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()
