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

import pytest
from _test_bedrock_chat_completion import (
    chat_completion_expected_events,
    chat_completion_get_llm_message_ids,
    chat_completion_payload_templates,
)
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_events import validate_ml_events

from newrelic.api.background_task import background_task
from newrelic.api.ml_model import get_llm_message_ids
from newrelic.api.transaction import add_custom_attribute, current_transaction


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
def expected_ai_message_ids(model_id):
    return chat_completion_get_llm_message_ids[model_id]


_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_with_convo_id(set_trace_info, exercise_model, expected_events):
    @validate_ml_events(expected_events)
    # One summary event, one user message, and one response message from the assistant
    @validate_ml_event_count(count=3)
    # @validate_transaction_metrics(
    #     name="test_bedrock_chat_completion_in_txn_with_convo_id",
    #     custom_metrics=[
    #         ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    #     ],
    #     background_task=True,
    # )
    @background_task(name="test_bedrock_chat_completion_in_txn_with_convo_id")
    def _test():
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_no_convo_id(set_trace_info, exercise_model, expected_events_no_convo_id):
    @validate_ml_events(expected_events_no_convo_id)
    # One summary event, one user message, and one response message from the assistant
    @validate_ml_event_count(count=3)
    # @validate_transaction_metrics(
    #     name="test_bedrock_chat_completion_in_txn_no_convo_id",
    #     custom_metrics=[
    #         ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    #     ],
    #     background_task=True,
    # )
    @background_task(name="test_bedrock_chat_completion_in_txn_no_convo_id")
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_bedrock_chat_completion_outside_txn(set_trace_info, exercise_model):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


disabled_ml_settings = {"machine_learning.enabled": False, "ml_insights_events.enabled": False}


@override_application_settings(disabled_ml_settings)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
# @validate_transaction_metrics(
#     name="test_bedrock_chat_completion_disabled_settings",
#     custom_metrics=[
#         ("Python/ML/OpenAI/%s" % openai.__version__, 1),
#     ],
#     background_task=True,
# )
@background_task(name="test_bedrock_chat_completion_disabled_settings")
def test_bedrock_chat_completion_disabled_settings(set_trace_info, exercise_model):
    set_trace_info()
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


# Testing get_llm_message_ids:


@reset_core_stats_engine()
@background_task()
def test_get_llm_message_ids_when_nr_message_ids_not_set():
    message_ids = get_llm_message_ids("request-id-1")
    assert message_ids == []


@reset_core_stats_engine()
def test_get_llm_message_ids_outside_transaction():
    message_ids = get_llm_message_ids("request-id-1")
    assert message_ids == []


@reset_core_stats_engine()
def test_get_llm_message_ids_bedrock_chat_completion_in_txn(
    set_trace_info, exercise_model, expected_ai_message_ids
):  # noqa: F811
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

        expected_message_ids = [value for value in expected_ai_message_ids.values()][0]
        message_ids = [m for m in get_llm_message_ids()]
        for index, message_id_info in enumerate(message_ids):
            expected_message_id_info = expected_message_ids[index]
            assert message_id_info["conversation_id"] == expected_message_id_info["conversation_id"]
            assert message_id_info["request_id"] == expected_message_id_info["request_id"]
            if expected_message_id_info["message_id"]:
                assert message_id_info["message_id"] == expected_message_id_info["message_id"]
            else:
                # We are checking for the presence of a message_id since in this case it is
                # a UUID that changes with each run.
                assert message_id_info["message_id"]

        assert current_transaction()._nr_message_ids == {}

    _test()


@reset_core_stats_engine()
def test_get_llm_message_ids_bedrock_chat_completion_no_convo_id(
    set_trace_info, exercise_model, expected_ai_message_ids
):  # noqa: F811
    @background_task()
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

        expected_message_ids = [value for value in expected_ai_message_ids.values()][0]
        message_ids = [m for m in get_llm_message_ids()]
        for index, message_id_info in enumerate(message_ids):
            expected_message_id_info = expected_message_ids[index]
            assert message_id_info["request_id"] == expected_message_id_info["request_id"]
            if expected_message_id_info["message_id"]:
                assert message_id_info["message_id"] == expected_message_id_info["message_id"]
            else:
                # We are checking for the presence of a message_id since in this case it is
                # a UUID that changes with each run.
                assert message_id_info["message_id"]
            assert message_id_info["conversation_id"] == ""

        assert current_transaction()._nr_message_ids == {}

    _test()