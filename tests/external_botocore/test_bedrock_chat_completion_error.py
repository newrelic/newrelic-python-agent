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

import botocore
import pytest
from _test_bedrock_chat_completion import (
    chat_completion_expected_events,
    chat_completion_payload_templates,
)
from test_bedrock_chat_completion import (
    exercise_model,
    is_file_payload,
    model_id,
)
from testing_support.fixtures import (
    dt_enabled,
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import add_custom_attribute, current_transaction
from newrelic.common.object_names import callable_name

_test_bedrock_chat_completion_prompt = "What is 212 degrees Fahrenheit converted to Celsius?"

chat_completion_payload_templates_no_prompt = {
    "amazon.titan-text-express-v1": '{ "textGenerationConfig": {"temperature": %f, "maxTokenCount": %d }}',
    "ai21.j2-mid-v1": '{"temperature": %f, "maxTokens": %d}',
    "cohere.command-text-v14": '{"temperature": %f, "max_tokens": %d}',
}


@pytest.fixture(scope="function")
def exercise_model_no_prompt(bedrock_server, model_id, is_file_payload):
    payload_template = chat_completion_payload_templates_no_prompt[model_id]

    def _exercise_model(temperature=0.7, max_tokens=100):
        breakpoint()
        body = (payload_template % (temperature, max_tokens)).encode("utf-8")
        if is_file_payload:
            body = BytesIO(body)

        bedrock_server.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
        )

    return _exercise_model


# No prompt provided
@dt_enabled
@reset_core_stats_engine()
# @validate_error_trace_attributes(
#     callable_name(botocore.InvalidRequestError),
#     exact_attrs={
#         "agent": {},
#         "intrinsic": {},
#         "user": {
#             # "api_key_last_four_digits": "sk-CRET",
#             # "request.temperature": 0.7,
#             # "request.max_tokens": 100,
#             # "vendor": "openAI",
#             # "ingest_source": "Python",
#             # "response.number_of_messages": 2,
#             # "error.param": "engine",
#         },
#     },
# )
# @validate_span_events(
#     exact_agents={
#         # "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>",
#     }
# )
def test_bedrock_chat_completion_no_prompt(exercise_model_no_prompt):
    @background_task()
    def _test():
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        exercise_model_no_prompt(temperature=0.7, max_tokens=100)

    _test()


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(botocore.InvalidSignatureException),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            # "request.id": "b61f5406-5955-4dc9-915c-9ae1bedda182", # This will change
            # "api_key_last_four_digits": "sk-CRET",
            # "request.model": None, # Grab from payload templates
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "Bedrock",
            "ingest_source": "Python",
            "http.statusCode": 403,
            "error.message": "The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.",
            "error.code": "InvalidSignatureException",
        },
    },
)
def test_bedrock_chat_completion_incorrect_secret_access_key(exercise_model):
    @background_task()
    def _test():
        with pytest.raises(botocore.InvalidSignatureException):  # not sure where this exception actually comes from
            set_trace_info()
            add_custom_attribute("conversation_id", "my-awesome-id")
            exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

    _test()


# @reset_core_stats_engine()
# def test_bedrock_chat_completion_in_txn(exercise_model, expected_events):
#     @background_task()
#     def _test():
#         set_trace_info()
#         add_custom_attribute("conversation_id", "my-awesome-id")
#         exercise_model(prompt=_test_bedrock_chat_completion_prompt, temperature=0.7, max_tokens=100)

#     _test()
