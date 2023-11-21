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
from testing_support.fixtures import dt_enabled, reset_core_stats_engine, validate_custom_event_count
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.api.transaction import add_custom_attribute


_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

# Sync tests:
no_model_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "completion_id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "", # No model in this test case
            "response.organization": None,
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 2,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "response.model": None,
            "completion_id": None,
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "response.model": None,
            "sequence": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]

# No model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "error.param": "engine",
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>",
   }
)
@validate_custom_events(no_model_events)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        openai.ChatCompletion.create(
            # no model provided,
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
        )


invalid_model_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "completion_id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist", # No model in this test case
            "response.organization": None,
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Model does not exist.",
            "role": "user",
            "response.model": None,
            "completion_id": None,
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]
# Invalid model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "error.code": "model_not_found",
            "http.statusCode": 404,
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "The model `does-not-exist` does not exist",
   }
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        openai.ChatCompletion.create(
            model="does-not-exist",
            messages=({"role": "user", "content": "Model does not exist."},),
            temperature=0.7,
            max_tokens=100,
        )

auth_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "completion_id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "api_key_last_four_digits": "",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo", # No model in this test case
            "response.organization": None,
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 2,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "You are a scientist.",
            "role": "system",
            "response.model": None,
            "completion_id": None,
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "my-awesome-id",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "response.model": None,
            "sequence": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]

# No api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details.",
   }
)
@validate_custom_events(auth_error_events)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_authentication_error(monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
        )



wrong_api_key_error_events = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "completion_id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "conversation_id": "",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "api_key_last_four_digits": "sk-BEEF",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo", # No model in this test case
            "response.organization": None,
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "appName": "Python Agent Test (mlmodel_openai)",
            "conversation_id": "",
            "request_id": None,
            "span_id": "span-id",
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "content": "Invalid API key.",
            "role": "user",
            "completion_id": None,
            "response.model": None,
            "sequence": 0,
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    ),
]
# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "Incorrect API key provided: invalid. You can find your API key at https://platform.openai.com/account/api-keys.",
  }
)
@validate_custom_events(wrong_api_key_error_events)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_wrong_api_key_error(monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=({"role": "user", "content": "Invalid API key."},),
            temperature=0.7,
            max_tokens=100,
        )


# Async tests:


# No model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "error.param": "engine",
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>",
   }
)
@validate_custom_events(no_model_events)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                # no model provided,
                messages=_test_openai_chat_completion_messages,
                temperature=0.7,
                max_tokens=100,
            )
        )


# Invalid model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "error.code": "model_not_found",
            "http.statusCode": 404,
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "The model `does-not-exist` does not exist",
   }
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                model="does-not-exist",
                messages=({"role": "user", "content": "Model does not exist."},),
                temperature=0.7,
                max_tokens=100,
            )
        )


# No api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details.",
   }
)
@validate_custom_events(auth_error_events)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_authentication_error_async(loop, monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        add_custom_attribute("conversation_id", "my-awesome-id")
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
            )
        )


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
        },
    },
)
@validate_span_events(
   exact_agents={
       "error.message": "Incorrect API key provided: invalid. You can find your API key at https://platform.openai.com/account/api-keys.",
   }
)
@validate_custom_events(wrong_api_key_error_events)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_wrong_api_key_error_async(loop, monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=({"role": "user", "content": "Invalid API key."},),
                temperature=0.7,
                max_tokens=100,
            )
        )
