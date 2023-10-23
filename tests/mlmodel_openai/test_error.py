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

import openai
import pytest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

enabled_ml_settings = {
    "machine_learning.enabled": True,
    "machine_learning.inference_events_value.enabled": True,
    "ml_insights_events.enabled": True,
    "error_collector.ignore_status_codes": [],
}

_test_openai_chat_completion_sync_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)


# No model provided
@override_application_settings(enabled_ml_settings)
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-CRET",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 2,
            "error.param": "engine",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>",
    }
)
@background_task()
def test_invalid_request_error_no_model():
    with pytest.raises(openai.InvalidRequestError):
        openai.ChatCompletion.create(
            # no model provided,
            messages=_test_openai_chat_completion_sync_messages,
            temperature=0.7,
            max_tokens=100,
        )


@override_application_settings(enabled_ml_settings)
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-CRET",
            "request.model": "does-not-exist",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
            "error.code": "model_not_found",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist",
    }
)
@validate_span_events(
    exact_agents={
        "http.statusCode": 404,
    }
)
@background_task()
def test_invalid_request_error_invalid_model():
    with pytest.raises(openai.InvalidRequestError):
        openai.ChatCompletion.create(
            model="does-not-exist",
            messages=({"role": "user", "content": "Model does not exist."},),
            temperature=0.7,
            max_tokens=100,
        )


# No api_key provided
@override_application_settings(enabled_ml_settings)
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 2,
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details.",
    }
)
@background_task()
def test_authentication_error(monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_sync_messages, temperature=0.7, max_tokens=100
        )


# Wrong api_key provided
@override_application_settings(enabled_ml_settings)
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-BEEF",
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "response.number_of_messages": 1,
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: invalid. You can find your API key at https://platform.openai.com/account/api-keys."
    }
)
@validate_span_events(
    exact_agents={
        "http.statusCode": 401,
    }
)
@background_task()
def test_wrong_api_key_error(monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=({"role": "user", "content": "Invalid API key."},),
            temperature=0.7,
            max_tokens=100,
        )
