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

# from io import BytesIO
# import json

# import pytest
# from newrelic.api.background_task import background_task
# from newrelic.api.time_trace import current_trace
# from newrelic.api.transaction import current_transaction, add_custom_attribute

# _test_bedrock_chat_completion_prompt = "Write me a blog about making strong business decisions as a leader."

# def set_trace_info():
#     txn = current_transaction()
#     if txn:
#         txn._trace_id = "trace-id"
#     trace = current_trace()
#     if trace:
#         trace.guid = "span-id"


# @pytest.mark.parametrize(
#     "model_id,payload",
#     [
#         ("amazon.titan-text-express-v1", {"inputText": "%s", "textGenerationConfig": {"temperature": 0.1, "maxTokenCount": 20}}),
#         # ("anthropic.claude-instant-v1", {"prompt": "Human: %s\n\nAssistant:", "max_tokens_to_sample": 500}),
#         # ("ai21.j2-mid-v1", {"prompt": "%s", "maxTokens": 200}),
#         # ("cohere.command-text-v14", {"prompt": "%s", "max_tokens": 200, "temperature": 0.75}),
#     ],
# )
# @pytest.mark.parametrize("is_file_payload", (False, True))
# @background_task()
# def test_bedrock_chat_completion(bedrock_server, model_id, payload, is_file_payload):
#     body = (json.dumps(payload) % _test_bedrock_chat_completion_prompt).encode("utf-8")
#     if is_file_payload:
#         body = BytesIO(body)

#     response = bedrock_server.invoke_model(
#         body=body,
#         modelId=model_id,
#         accept="application/json",
#         contentType="application/json",
#     )
#     response_body = json.loads(response.get("body").read())
#     assert response_body




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

from io import BytesIO

import json
import pytest
from testing_support.fixtures import (  # function_not_called,; override_application_settings,
    function_not_called,
    override_application_settings,
    reset_core_stats_engine,
)

from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, add_custom_attribute
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_event_payload import (
    validate_ml_event_payload,
)
from testing_support.validators.validate_ml_events import validate_ml_events
from testing_support.validators.validate_ml_events_outside_transaction import (
    validate_ml_events_outside_transaction,
)

import newrelic.core.otlp_utils
from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_ml_event
from newrelic.core.config import global_settings
from newrelic.packages import six


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


@pytest.fixture(scope="session", params=[
    ("amazon.titan-text-express-v1", '{ "inputText": "%s", "textGenerationConfig": {"temperature": %f, "maxTokenCount": %d }}'),
    # ("anthropic.claude-instant-v1", '{"prompt": "Human: {prompt}\n\nAssistant:", "max_tokens_to_sample": {max_tokens:d}}'),
    # ("ai21.j2-mid-v1", '{"prompt": "{prompt}", "maxTokens": {max_tokens:d}}'),
    # ("cohere.command-text-v14", '{"prompt": "{prompt}", "max_tokens": {max_tokens:d}, "temperature": {temperature:f}}'),
])
def exercise_model(request, bedrock_server, is_file_payload):
    def _exercise_model(prompt, temperature=0.7, max_tokens=100):
        model_id, payload_template = request.param
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


_test_openai_chat_completion_sync_messages = "What is 212 degrees Fahrenheit converted to Celsius?"


sync_chat_completion_recorded_events = [
    (
        {'type': 'LlmChatCompletionSummary'},
        {
            'id': None, # UUID that varies with each run
            'appName': 'Python Agent Test (mlmodel_bedrock)',
            'conversation_id': 'my-awesome-id',
            'transaction_id': None,
            'span_id': "span-id",
            'trace_id': "trace-id",
            'request_id': None,  # Varies each time
            'access_key_last_four_digits': None,  # Varies each time
            'duration': None,  # Response time varies each test run
            'request.model': 'amazon.titan-text-express-v1',
            'response.model': 'amazon.titan-text-express-v1',
            'response.usage.completion_tokens': None,
            'response.usage.total_tokens': None,
            'response.usage.prompt_tokens': None,
            'request.temperature': 0.7,
            'request.max_tokens': 100,
            'response.choices.finish_reason': 'FINISH',
            'vendor': 'bedrock',
            'ingest_source': 'Python',
            'number_of_messages': 2,
        },
    ),
    (
        {'type': 'LlmChatCompletionMessage'},
        {
            'id': None, # UUID that varies with each run
            'appName': 'Python Agent Test (mlmodel_bedrock)',
            'request_id': None,  # Varies each time
            'span_id': "span-id",
            'trace_id': "trace-id",
            'transaction_id': None,
            'content': 'What is 212 degrees Fahrenheit converted to Celsius?',
            'role': 'user',
            'completion_id': None,
            'sequence': 0,
            'response.model': 'amazon.titan-text-express-v1',
            'vendor': 'bedrock',
            'ingest_source': 'Python'
        },
    ),
    (
        {'type': 'LlmChatCompletionMessage'},
        {
            'id': None, # UUID that varies with each run
            'appName': 'Python Agent Test (mlmodel_bedrock)',
            'request_id': None,  # Varies each time
            'span_id': "span-id",
            'trace_id': "trace-id",
            'transaction_id': None,
            'content': None,
            'role': 'assistant',
            'completion_id': None,
            'sequence': 1,
            'response.model': 'amazon.titan-text-express-v1',
            'vendor': 'bedrock',
            'ingest_source': 'Python'
        }
    ),
]


@reset_core_stats_engine()
@validate_ml_events(sync_chat_completion_recorded_events)
# One summary event, one user message, and one response message from the assistant
@validate_ml_event_count(count=3)
@background_task()
def test_openai_chat_completion_sync_in_txn(exercise_model):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    exercise_model(
        prompt=_test_openai_chat_completion_sync_messages,
        temperature=0.7,
        max_tokens=100
    )


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_chat_completion_sync_outside_txn(exercise_model):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    exercise_model(
        prompt=_test_openai_chat_completion_sync_messages,
        temperature=0.7,
        max_tokens=100
    )


disabled_ml_settings = {
    "machine_learning.enabled": False,
    "ml_insights_events.enabled": False
}


@override_application_settings(disabled_ml_settings)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_chat_completion_sync_disabled_settings(exercise_model):
    set_trace_info()
    exercise_model(
        prompt=_test_openai_chat_completion_sync_messages,
        temperature=0.7,
        max_tokens=100
    )


# def test_openai_chat_completion_async(loop):
#     loop.run_until_complete(
#         openai.ChatCompletion.acreate(
#             model="amazon.titan-text-express-v1",
#             messages=_test_openai_chat_completion_sync_messages,
#         )
#     )
