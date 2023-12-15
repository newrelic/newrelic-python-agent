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
import sys
from testing_support.fixtures import (
    dt_enabled,
    reset_core_stats_engine,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name


# Sync tests:
no_model_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "This is an embedding test with no model.",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "",  # No model in this test case
            "response.organization": "",
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "create() missing 1 required keyword-only argument: 'model'" if sys.version_info < (3, 10) else "Embeddings.create() missing 1 required keyword-only argument: 'model'",
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error_v1:test_embeddings_invalid_request_error_no_model",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_custom_events(no_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model(set_trace_info, sync_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        sync_openai_client.embeddings.create(input="This is an embedding test with no model.")  # no model provided


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "create() missing 1 required keyword-only argument: 'model'" if sys.version_info < (3, 10) else "AsyncEmbeddings.create() missing 1 required keyword-only argument: 'model'",
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error_v1:test_embeddings_invalid_request_error_no_model_async",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_custom_events(no_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model_async(set_trace_info, async_openai_client, loop):
    with pytest.raises(TypeError):
        set_trace_info()
        loop.run_until_complete(
            async_openai_client.embeddings.create(input="This is an embedding test with no model.")
        )  # no model provided


invalid_model_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "Model does not exist.",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",
            "response.organization": None,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InternalServerError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Unknown Prompt:\nModel does not exist.",
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error_v1:test_embeddings_invalid_request_error_invalid_model",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model(set_trace_info, sync_openai_client):
    with pytest.raises(openai.InternalServerError):
        set_trace_info()
        sync_openai_client.embeddings.create(input="Model does not exist.", model="does-not-exist")


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InternalServerError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Unknown Prompt:\nModel does not exist.",
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error_v1:test_embeddings_invalid_request_error_invalid_model_async",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model_async(set_trace_info, async_openai_client, loop):
    with pytest.raises(openai.InternalServerError):
        set_trace_info()
        loop.run_until_complete(
            async_openai_client.embeddings.create(input="Model does not exist.", model="does-not-exist")
        )


embedding_invalid_key_error_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "Invalid API key.",
            "api_key_last_four_digits": "sk-BEEF",
            "duration": None,  # Response time varies each test run
            "request.model": "text-embedding-ada-002",
            "response.organization": None,
            "vendor": "openAI",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
            "error.code": "invalid_api_key",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error_v1:test_embeddings_wrong_api_key_error",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_custom_events(embedding_invalid_key_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_wrong_api_key_error(set_trace_info, monkeypatch, sync_openai_client):
    with pytest.raises(openai.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(sync_openai_client, "api_key", "DEADBEEF")
        sync_openai_client.embeddings.create(input="Invalid API key.", model="text-embedding-ada-002")


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.AuthenticationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {
            "http.statusCode": 401,
            "error.code": "invalid_api_key",
        },
    },
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys.",
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error_v1:test_embeddings_wrong_api_key_error_async",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_custom_events(embedding_invalid_key_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_wrong_api_key_error_async(set_trace_info, monkeypatch, async_openai_client, loop):
    with pytest.raises(openai.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(async_openai_client, "api_key", "DEADBEEF")
        loop.run_until_complete(
            async_openai_client.embeddings.create(input="Invalid API key.", model="text-embedding-ada-002")
        )
