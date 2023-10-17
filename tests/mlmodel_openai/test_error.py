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

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

enabled_ml_settings = {
    "machine_learning.enabled": True,
    "machine_learning.inference_events_value.enabled": True,
    "ml_insights_events.enabled": True,
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
            "id": "None",
            "api_key_last_four_digits": "sk-CRET",
            "request.model": "None",
            "temperature": 0.7,
            "max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "organization": "None",
            "number_of_messages": 2,
            "status_code": "None",
            "error_message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>",
            "error_type": "InvalidRequestError",
            "error_code": "None",
            "error_param": "engine",
        },
    },
)
@background_task()
def test_invalid_request_error():
    with pytest.raises(openai.InvalidRequestError):
        openai.ChatCompletion.create(
            # no model provided,
            messages=_test_openai_chat_completion_sync_messages,
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
            "id": "None",
            "api_key_last_four_digits": "None",
            "request.model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "organization": "None",
            "number_of_messages": 2,
            "status_code": "None",
            "error_message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_pa",
            "error_type": "AuthenticationError",
            "error_code": "None",
            "error_param": "None",
        },
    },
)
@background_task()
def test_authentication_error(monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_sync_messages, temperature=0.7, max_tokens=100
        )


# Incorrect URL provided (404 error)
@override_application_settings(enabled_ml_settings)
@validate_error_trace_attributes(
    callable_name(openai.error.APIError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "id": "None",
            "api_key_last_four_digits": "sk-CRET",
            "request.model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 100,
            "vendor": "openAI",
            "ingest_source": "Python",
            "organization": "None",
            "number_of_messages": 2,
            "status_code": 404,
            "error_message": 'HTTP code 404 from API (<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html><head>\n<title>404 Not Found</title>\n</head><body>\n<h1>Not Found</h1>\n<p>The requested URL was not found on this server.</p>\n<hr>\n<address>Apache/2.4.25 (Debian) Server at thi',
            "error_type": "APIError",
            "error_code": 404,
            "error_param": "None",
        },
    },
)
@background_task()
def test_api_error():
    openai.api_base = "http://thisisnotarealurl.com/"
    with pytest.raises(openai.error.APIError):
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_sync_messages,
            temperature=0.7,
            max_tokens=100,
        )


# Timeout is raised by requests.exceptions.Timeout
# APIConnectionError is raised by requests.exceptions.RequestException
