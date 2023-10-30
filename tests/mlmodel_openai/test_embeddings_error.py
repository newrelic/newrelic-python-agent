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
from newrelic.common.object_names import callable_name

enabled_ml_settings = {
    "machine_learning.enabled": True,
    "machine_learning.inference_events_value.enabled": True,
    "ml_insights_events.enabled": True,
    "error_collector.ignore_status_codes": set(),
}


# Sync tests:


# No model provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-CRET",
            "vendor": "openAI",
            "ingest_source": "Python",
            "error.param": "engine",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.embedding.Embedding'>",
    }
)
@background_task()
def test_embeddings_invalid_request_error_no_model():
    with pytest.raises(openai.InvalidRequestError):
        openai.Embedding.create(
            input="This is an embedding test with no model.",
            # no model provided
        )


# Invalid model provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-CRET",
            "request.model": "does-not-exist",
            "vendor": "openAI",
            "ingest_source": "Python",
            "error.code": "model_not_found",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist",
        "http.statusCode": 404,
    }
)
@background_task()
def test_embeddings_invalid_request_error_invalid_model():
    with pytest.raises(openai.InvalidRequestError):
        openai.Embedding.create(input="Model does not exist.", model="does-not-exist")


# No api_key provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "request.model": "text-embedding-ada-002",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details.",
    }
)
@background_task()
def test_embeddings_authentication_error(monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        openai.Embedding.create(input="Invalid API key.", model="text-embedding-ada-002")


# Wrong api_key provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-BEEF",
            "request.model": "text-embedding-ada-002",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
        "http.statusCode": 401,
    }
)
@background_task()
def test_embeddings_wrong_api_key_error(monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        openai.Embedding.create(input="Embedded: Invalid API key.", model="text-embedding-ada-002")


# Async tests:


# No model provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-CRET",
            "vendor": "openAI",
            "ingest_source": "Python",
            "error.param": "engine",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.embedding.Embedding'>",
    }
)
@background_task()
def test_embeddings_invalid_request_error_no_model_async(loop):
    with pytest.raises(openai.InvalidRequestError):
        loop.run_until_complete(
            openai.Embedding.acreate(
                input="This is an embedding test with no model.",
                # No model provided
            )
        )


# Invalid model provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-CRET",
            "request.model": "does-not-exist",
            "vendor": "openAI",
            "ingest_source": "Python",
            "error.code": "model_not_found",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist",
        "http.statusCode": 404,
    }
)
@background_task()
def test_embeddings_invalid_request_error_invalid_model_async(loop):
    with pytest.raises(openai.InvalidRequestError):
        loop.run_until_complete(openai.Embedding.acreate(input="Model does not exist.", model="does-not-exist"))


# No api_key provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "request.model": "text-embedding-ada-002",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>). If your API key is stored in a file, you can point the openai module at it with 'openai.api_key_path = <PATH>'. You can generate API keys in the OpenAI web interface. See https://platform.openai.com/account/api-keys for details.",
    }
)
@background_task()
def test_embeddings_authentication_error_async(loop, monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        loop.run_until_complete(openai.Embedding.acreate(input="Invalid API key.", model="text-embedding-ada-002"))


# Wrong api_key provided
@override_application_settings(enabled_ml_settings)
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "api_key_last_four_digits": "sk-BEEF",
            "request.model": "text-embedding-ada-002",
            "vendor": "openAI",
            "ingest_source": "Python",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
        "http.statusCode": 401,
    }
)
@background_task()
def test_embeddings_wrong_api_key_error_async(loop, monkeypatch):
    with pytest.raises(openai.error.AuthenticationError):
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        loop.run_until_complete(
            openai.Embedding.acreate(input="Embedded: Invalid API key.", model="text-embedding-ada-002")
        )
