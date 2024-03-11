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
from _test_bedrock_embeddings import (
    embedding_expected_client_errors,
    embedding_expected_error_events,
    embedding_expected_events,
    embedding_payload_templates,
)
from conftest import (  # pylint: disable=E0611
    BOTOCORE_VERSION,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
)
from testing_support.fixtures import (  # override_application_settings,
    dt_enabled,
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


@pytest.fixture(scope="session", params=[False, True], ids=["Bytes", "Stream"])
def is_file_payload(request):
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
def exercise_model(bedrock_server, model_id, is_file_payload):
    payload_template = embedding_payload_templates[model_id]

    def _exercise_model(prompt, temperature=0.7, max_tokens=100):
        body = (payload_template % prompt).encode("utf-8")
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
    return embedding_expected_events[model_id]


@pytest.fixture(scope="module")
def expected_events_no_content(model_id):
    events = copy.deepcopy(embedding_expected_events[model_id])
    for event in events:
        del event[1]["input"]
    return events


@pytest.fixture(scope="module")
def expected_error_events(model_id):
    return embedding_expected_error_events[model_id]


@pytest.fixture(scope="module")
def expected_error_events_no_content(model_id):
    events = copy.deepcopy(embedding_expected_error_events[model_id])
    for event in events:
        del event[1]["input"]
    return events


@pytest.fixture(scope="module")
def expected_client_error(model_id):
    return embedding_expected_client_errors[model_id]


@reset_core_stats_engine()
def test_bedrock_embedding(set_trace_info, exercise_model, expected_events):
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

        exercise_model(prompt="This is an embedding test.")

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_embedding_no_content(set_trace_info, exercise_model, expected_events_no_content):
    @validate_custom_events(expected_events_no_content)
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
    exercise_model(prompt="This is an embedding test.")


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_bedrock_embedding_disabled_ai_monitoring_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt="This is an embedding test.")


_client_error = botocore.exceptions.ClientError
_client_error_name = callable_name(_client_error)


@dt_enabled
@reset_core_stats_engine()
def test_bedrock_embedding_error_incorrect_access_key(
    monkeypatch, bedrock_server, exercise_model, set_trace_info, expected_error_events, expected_client_error
):
    @validate_custom_events(expected_error_events)
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

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
def test_bedrock_embedding_error_incorrect_access_key_no_content(
    monkeypatch, bedrock_server, exercise_model, set_trace_info, expected_error_events_no_content, expected_client_error
):
    @validate_custom_events(expected_error_events_no_content)
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

        with pytest.raises(_client_error):  # not sure where this exception actually comes from
            set_trace_info()
            exercise_model(prompt="Invalid Token", temperature=0.7, max_tokens=100)

    _test()


def test_bedrock_chat_completion_functions_marked_as_wrapped_for_sdk_compatibility(bedrock_server):
    assert bedrock_server._nr_wrapped
