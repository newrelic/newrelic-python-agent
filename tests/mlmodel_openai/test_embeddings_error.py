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
            "input": "This is an embedding test with no model.",
            "duration": None,  # Response time varies each test run
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    )
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
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.embedding.Embedding'>"
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_no_model",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        openai.Embedding.create(
            input="This is an embedding test with no model."
            # no model provided
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
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.embedding.Embedding'>"
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_no_model_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model_no_content(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        openai.Embedding.create(
            input="This is an embedding test with no model."
            # no model provided
        )


invalid_model_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "input": "Model does not exist.",
            "duration": None,  # Response time varies each test run
            "request.model": "does-not-exist",  # No model in this test case
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    )
]


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 404}},
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist"
        # "http.statusCode": 404,
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_invalid_model_with_token_count",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(add_token_count_to_events(invalid_model_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model_with_token_count(set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        openai.Embedding.create(input="Model does not exist.", model="does-not-exist")


# Invalid model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 404}},
)
@validate_span_events(
    exact_agents={
        "error.message": "The model `does-not-exist` does not exist"
        # "http.statusCode": 404,
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_invalid_model",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model(set_trace_info):
    set_trace_info()
    with pytest.raises(openai.InvalidRequestError):
        openai.Embedding.create(input="Model does not exist.", model="does-not-exist")


embedding_auth_error_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "input": "Invalid API key.",
            "duration": None,  # Response time varies each test run
            "request.model": "text-embedding-ada-002",  # No model in this test case
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    )
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
    name="test_embeddings_error:test_embeddings_authentication_error",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_auth_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_authentication_error(monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        openai.Embedding.create(input="Invalid API key.", model="text-embedding-ada-002")


embedding_invalid_key_error_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "input": "Embedded: Invalid API key.",
            "duration": None,  # Response time varies each test run
            "request.model": "text-embedding-ada-002",  # No model in this test case
            "vendor": "openai",
            "ingest_source": "Python",
            "error": True,
        },
    )
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
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys."
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_wrong_api_key_error",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_invalid_key_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_wrong_api_key_error(monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        openai.Embedding.create(input="Embedded: Invalid API key.", model="text-embedding-ada-002")


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
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.embedding.Embedding'>"
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_no_model_async",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        loop.run_until_complete(
            openai.Embedding.acreate(
                input="This is an embedding test with no model."
                # No model provided
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
        "error.message": "Must provide an 'engine' or 'model' parameter to create a <class 'openai.api_resources.embedding.Embedding'>"
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_no_model_async_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_no_model_async_no_content(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        loop.run_until_complete(
            openai.Embedding.acreate(
                input="This is an embedding test with no model."
                # No model provided
            )
        )


@dt_enabled
@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 404}},
)
@validate_span_events(exact_agents={"error.message": "The model `does-not-exist` does not exist"})
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_invalid_model_with_token_count_async",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(add_token_count_to_events(invalid_model_events))
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model_with_token_count_async(set_trace_info, loop):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        loop.run_until_complete(openai.Embedding.acreate(input="Model does not exist.", model="does-not-exist"))


# Invalid model provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.InvalidRequestError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 404}},
)
@validate_span_events(exact_agents={"error.message": "The model `does-not-exist` does not exist"})
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_invalid_request_error_invalid_model_async",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(invalid_model_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_invalid_request_error_invalid_model_async(loop, set_trace_info):
    with pytest.raises(openai.InvalidRequestError):
        set_trace_info()
        loop.run_until_complete(openai.Embedding.acreate(input="Model does not exist.", model="does-not-exist"))


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
    name="test_embeddings_error:test_embeddings_authentication_error_async",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_auth_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_authentication_error_async(loop, monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(openai, "api_key", None)  # openai.api_key = None
        loop.run_until_complete(openai.Embedding.acreate(input="Invalid API key.", model="text-embedding-ada-002"))


# Wrong api_key provided
@dt_enabled
@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(openai.error.AuthenticationError),
    exact_attrs={"agent": {}, "intrinsic": {}, "user": {"http.statusCode": 401}},
)
@validate_span_events(
    exact_agents={
        "error.message": "Incorrect API key provided: DEADBEEF. You can find your API key at https://platform.openai.com/account/api-keys."
    }
)
@validate_transaction_metrics(
    name="test_embeddings_error:test_embeddings_wrong_api_key_error_async",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_custom_events(embedding_invalid_key_error_events)
@validate_custom_event_count(count=1)
@background_task()
def test_embeddings_wrong_api_key_error_async(loop, monkeypatch, set_trace_info):
    with pytest.raises(openai.error.AuthenticationError):
        set_trace_info()
        monkeypatch.setattr(openai, "api_key", "DEADBEEF")  # openai.api_key = "DEADBEEF"
        loop.run_until_complete(
            openai.Embedding.acreate(input="Embedded: Invalid API key.", model="text-embedding-ada-002")
        )
