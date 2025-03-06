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

import google.genai
import pytest
from testing_support.fixtures import dt_enabled, override_llm_token_callback_settings, reset_core_stats_engine
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
    disabled_ai_monitoring_record_content_settings,
    events_sans_content,
    llm_token_count_callback,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

embedding_recorded_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "contents": "This is an embedding test with no model.",
            "duration": None,  # Response time varies each test run
            "vendor": "gemini",
            "ingest_source": "Python",
            "error": True,
        },
    )
]


# No model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {}},
)
@validate_span_events(
    exact_agents={"error.message": "Models.embed_content() missing 1 required keyword-only argument: 'model'"}
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_no_model",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model(set_trace_info):
    with pytest.raises(TypeError):
        set_trace_info()
        client.models.embed_content(
            contents="This is an embedding test with no model.",
            # No model
        )


@dt_enabled
@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {}},
)
@validate_span_events(
    exact_agents={"error.message": "Models.embed_content() missing 1 required keyword-only argument: 'model'"}
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_no_model_no_content",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model_no_content(set_trace_info):
    with pytest.raises(TypeError):
        set_trace_info()
        client.models.embed_content(
            contents="This is an embedding test with no model.",
            # no model provided
        )


invalid_model_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "contents": "Model does not exist.",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",  # No model in this test case
            "vendor": "gemini",
            "ingest_source": "Python",
            "error": True,
        },
    )
]


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "NOT_FOUND", "http.statusCode": 404}},
)
@validate_span_events(
    exact_agents={
        "error.message": "models/does-not-exist is not found for API version v1beta, or is not supported for embedContent. Call ListModels to see the list of available models and their supported methods."
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_invalid_model",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model(set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        client.models.embed_content(contents="Model does not exist.", model="does-not-exist")


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "NOT_FOUND", "http.statusCode": 404}},
)
@validate_span_events(
    exact_agents={
        "error.message": "models/does-not-exist is not found for API version v1beta, or is not supported for embedContent. Call ListModels to see the list of available models and their supported methods."
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_invalid_model_with_token_count",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(add_token_count_to_events(invalid_model_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model_with_token_count(set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        client.models.embed_content(contents="Model does not exist.", model="does-not-exist")


embedding_invalid_key_error_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "contents": "Embedded: Invalid API key.",
            "duration": None,  # Response time varies each test run
            "request.model": "text-embedding-004",  # No model in this test case
            "vendor": "gemini",
            "ingest_source": "Python",
            "error": True,
        },
    )
]


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "INVALID_ARGUMENT", "http.statusCode": 400}},
)
@validate_span_events(exact_agents={"error.message": "API key not valid. Please pass a valid API key."})
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_wrong_api_key_error",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_invalid_key_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_wrong_api_key_error(monkeypatch, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        bad_client = google.genai.Client(api_key="DEADBEEF")
        bad_client.models.embed_content(contents="Embedded: Invalid API key.", model="text-embedding-004")


# # Async tests:
# No model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {}},
)
@validate_span_events(
    exact_agents={"error.message": "Models.embed_content() missing 1 required keyword-only argument: 'model'"}
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_async_invalid_request_error_no_model",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_async_invalid_request_error_no_model(loop, set_trace_info):
    with pytest.raises(TypeError):
        set_trace_info()
        loop.run_until_complete(
            client.models.embed_content(
                contents="This is an embedding test with no model.",
                # No model
            )
        )


@dt_enabled
@disabled_ai_monitoring_record_content_settings
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {}},
)
@validate_span_events(
    exact_agents={"error.message": "Models.embed_content() missing 1 required keyword-only argument: 'model'"}
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_async_invalid_request_error_no_model_no_content",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_async_invalid_request_error_no_model_no_content(loop, set_trace_info):
    with pytest.raises(TypeError):
        set_trace_info()
        loop.run_until_complete(
            client.models.embed_content(
                contents="This is an embedding test with no model.",
                # no model provided
            )
        )


@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "NOT_FOUND", "http.statusCode": 404}},
)
@validate_span_events(
    exact_agents={
        "error.message": "models/does-not-exist is not found for API version v1beta, or is not supported for embedContent. Call ListModels to see the list of available models and their supported methods."
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_async_invalid_request_error_invalid_model",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_async_invalid_request_error_invalid_model(loop, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        loop.run_until_complete(client.models.embed_content(contents="Model does not exist.", model="does-not-exist"))


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "NOT_FOUND", "http.statusCode": 404}},
)
@validate_span_events(
    exact_agents={
        "error.message": "models/does-not-exist is not found for API version v1beta, or is not supported for embedContent. Call ListModels to see the list of available models and their supported methods."
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_async_invalid_request_error_invalid_model_with_token_count",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(add_token_count_to_events(invalid_model_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_async_invalid_request_error_invalid_model_with_token_count(loop, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        loop.run_until_complete(client.models.embed_content(contents="Model does not exist.", model="does-not-exist"))


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(google.genai.errors.ClientError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"error.code": "INVALID_ARGUMENT", "http.statusCode": 400}},
)
@validate_span_events(exact_agents={"error.message": "API key not valid. Please pass a valid API key."})
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_async_wrong_api_key_error",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(f"Supportability/Python/ML/Gemini/{google.genai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_invalid_key_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_async_wrong_api_key_error(loop, monkeypatch, set_trace_info):
    with pytest.raises(google.genai.errors.ClientError):
        set_trace_info()
        bad_client = google.genai.Client(api_key="DEADBEEF")
        loop.run_until_complete(
            bad_client.models.embed_content(contents="Embedded: Invalid API key.", model="text-embedding-004")
        )
