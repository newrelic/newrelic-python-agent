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
from testing_support.fixtures import dt_enabled, override_llm_token_callback_settings, reset_core_stats_engine
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
    disabled_ai_monitoring_record_content_settings,
    events_sans_content,
    events_with_context_attrs,
    llm_token_count_callback,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name

_test_openai_chat_completion_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)

expected_events_on_no_model_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 2,
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
]


# No model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.param": "engine"}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>"
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_no_model",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_with_context_attrs(expected_events_on_no_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        with WithLlmCustomAttributes({"context": "attr"}):
            openai.ChatCompletion.create(
                # no model provided,
                messages=_test_openai_chat_completion_messages,
                temperature=0.7,
                max_tokens=100,
            )


@dt_enabled
@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.param": "engine"}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>"
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_no_model_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_no_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_no_content(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        openai.ChatCompletion.create(
            # no model provided,
            messages=_test_openai_chat_completion_messages,
            temperature=0.7,
            max_tokens=100,
        )


expected_events_on_invalid_model_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "Model does not exist.",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "model_not_found", "http.statusCode": 404}},
)
@validate_span_events(exact_agents={"error.message": "The model `does-not-exist` does not exist"})
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_invalid_model_with_token_count",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(add_token_count_to_events(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model_with_token_count(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")

        openai.ChatCompletion.create(
            model="does-not-exist",
            messages=({"role": "user", "content": "Model does not exist."},),
            temperature=0.7,
            max_tokens=100,
        )


# Invalid model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "model_not_found", "http.statusCode": 404}},
)
@validate_span_events(exact_agents={"error.message": "The model `does-not-exist` does not exist"})
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_invalid_model",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_invalid_model_error)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        openai.ChatCompletion.create(
            model="does-not-exist",
            messages=({"role": "user", "content": "Model does not exist."},),
            temperature=0.7,
            max_tokens=100,
        )


expected_events_on_auth_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 2,
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "You are a scientist.",
            "role": "system",
            "completion_id": None,
            "sequence": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "llm.conversation_id": "my-awesome-id",
            "span_id": None,
            "trace_id": "trace-id",
            "content": "What is 212 degrees Fahrenheit converted to Celsius?",
            "role": "user",
            "completion_id": None,
            "sequence": 1,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
]


# No api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_span_events(
    exact_agents={
        "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details."
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_authentication_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_auth_error)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_authentication_error(monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=_test_openai_chat_completion_messages, temperature=0.7, max_tokens=100
        )


expected_events_on_wrong_api_key_error = [
    (
        {"type": "LlmChatCompletionSummary"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "duration": None,  # Response time varies each test run
            "request.model": "gpt-3.5-turbo",
            "request.temperature": 0.7,
            "request.max_tokens": 100,
            "response.number_of_messages": 1,
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    ),
    (
        {"type": "LlmChatCompletionMessage"},
        {
            "id": None,
            "span_id": None,
            "trace_id": "trace-id",
            "content": "Invalid API key.",
            "role": "user",
            "completion_id": None,
            "sequence": 0,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
]


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 401}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: invalid. You can find your API key at https://platform.openai.com/account/api-keys."
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_wrong_api_key_error",
    scoped_metrics=[("Llm/completion/OpenAI/create", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/create", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_wrong_api_key_error)
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
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.param": "engine"}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>"
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_no_model_async",
    scoped_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_no_model_error)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                # no model provided,
                messages=_test_openai_chat_completion_messages,
                temperature=0.7,
                max_tokens=100,
            )
        )


@dt_enabled
@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.param": "engine"}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.chat_completion.ChatCompletion'>"
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_no_model_async_no_content",
    scoped_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(expected_events_on_no_model_error))
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_invalid_request_error_no_model_async_no_content(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                # no model provided,
                messages=_test_openai_chat_completion_messages,
                temperature=0.7,
                max_tokens=100,
            )
        )


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "model_not_found", "http.statusCode": 404}},
)
@validate_span_events(exact_agents={"error.message": "The model `does-not-exist` does not exist"})
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_invalid_model_with_token_count_async",
    scoped_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    background_task=True,
)
@validate_custom_events(add_token_count_to_events(expected_events_on_invalid_model_error))
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model_with_token_count_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        loop.run_until_complete(
            openai.ChatCompletion.acreate(
                model="does-not-exist",
                messages=({"role": "user", "content": "Model does not exist."},),
                temperature=0.7,
                max_tokens=100,
            )
        )


# Invalid model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "model_not_found", "http.statusCode": 404}},
)
@validate_span_events(exact_agents={"error.message": "The model `does-not-exist` does not exist"})
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_invalid_request_error_invalid_model_async",
    scoped_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_invalid_model_error)
@validate_custom_event_count(count=2)
@background_task()
def test_chat_completion_invalid_request_error_invalid_model_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
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
    callable_name(openai.error.AuthenticationError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_span_events(
    exact_agents={
        "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details."
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_authentication_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_auth_error)
@validate_custom_event_count(count=3)
@background_task()
def test_chat_completion_authentication_error_async(loop, monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
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
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 401}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: invalid. You can find your API key at https://platform.openai.com/account/api-keys."
    }
)
@validate_transaction_metrics(
    "test_chat_completion_error:test_chat_completion_wrong_api_key_error_async",
    scoped_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/completion/OpenAI/acreate", 1)],
    background_task=True,
)
@validate_custom_events(expected_events_on_wrong_api_key_error)
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
