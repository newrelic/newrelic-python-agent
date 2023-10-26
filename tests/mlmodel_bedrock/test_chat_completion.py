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

import pytest
from _test_chat_completion import (
    chat_completion_expected_events,
    chat_completion_expected_events_no_convo_id,
    chat_completion_payload_templates,
)
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_events import validate_ml_events

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import add_custom_attribute, current_transaction


def set_trace_info():
    txn = current_transaction()
    if txn:
        txn._trace_id = "trace-id"
    trace = current_trace()
    if trace:
        trace.guid = "span-id"


@pytest.fixture(scope="session", params=[False, True])
def is_file_payload(request):
    return request.param


@pytest.fixture(
    scope="session",
    params=[
        "amazon.titan-text-express-v1",
        # ("anthropic.claude-instant-v1", '{"prompt": "Human: {prompt}\n\nAssistant:", "max_tokens_to_sample": {max_tokens:d}}'),
        # ("ai21.j2-mid-v1", '{"prompt": "{prompt}", "maxTokens": {max_tokens:d}}'),
        # ("cohere.command-text-v14", '{"prompt": "{prompt}", "max_tokens": {max_tokens:d}, "temperature": {temperature:f}}'),
    ],
)
def model_id(request):
    return request.param


@pytest.fixture(scope="session")
def exercise_model(bedrock_server, is_file_payload, model_id):
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


@pytest.fixture(scope="session")
def expected_events(model_id):
    return chat_completion_expected_events[model_id]


@pytest.fixture(scope="session")
def expected_events_no_convo_id(model_id):
    return chat_completion_expected_events_no_convo_id[model_id]


_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn(exercise_model, expected_events):
    @validate_ml_events(expected_events)
    # One summary event, one user message, and one response message from the assistant
    @validate_ml_event_count(count=3)
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
def test_bedrock_chat_completion_in_txn_no_convo_id(exercise_model, expected_events_no_convo_id):
    @validate_ml_events(expected_events_no_convo_id)
    # One summary event, one user message, and one response message from the assistant
    @validate_ml_event_count(count=3)
    @background_task()
    def _test():
        set_trace_info()
        exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_bedrock_chat_completion_outside_txn(exercise_model):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)


disabled_ml_settings = {"machine_learning.enabled": False, "ml_insights_events.enabled": False}


@override_application_settings(disabled_ml_settings)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_bedrock_chat_completion_disabled_settings(exercise_model):
    set_trace_info()
    exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)
