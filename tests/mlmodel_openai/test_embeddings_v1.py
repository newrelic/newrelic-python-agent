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
from testing_support.fixtures import override_llm_token_callback_settings, reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    add_token_count_to_events,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_sans_content,
    llm_token_count_callback,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

embedding_recorded_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "input": "This is an embedding test.",
            "duration": None,  # Response time varies each test run
            "response.model": "text-embedding-ada-002",
            "request.model": "text-embedding-ada-002",
            "request_id": "req_eb2b9f2d23a671ad0d69545044437d68",
            "response.organization": "new-relic-nkmd8b",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 3000,
            "response.headers.ratelimitLimitTokens": 1000000,
            "response.headers.ratelimitResetTokens": "0s",
            "response.headers.ratelimitResetRequests": "20ms",
            "response.headers.ratelimitRemainingTokens": 999994,
            "response.headers.ratelimitRemainingRequests": 2999,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    )
]


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_with_raw_response",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_with_raw_response(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.with_raw_response.create(
        input="This is an embedding test.", model="text-embedding-ada-002"
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_with_token_count",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_with_token_count(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_embedding_sync_outside_txn(sync_openai_client):
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_embedding_sync_ai_monitoring_disabled(sync_openai_client):
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_async",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async(loop, set_trace_info, async_openai_client):
    set_trace_info()

    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_async_with_raw_response",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async_with_raw_response(loop, set_trace_info, async_openai_client):
    set_trace_info()

    loop.run_until_complete(
        async_openai_client.embeddings.with_raw_response.create(
            input="This is an embedding test.", model="text-embedding-ada-002"
        )
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_async_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async_no_content(loop, set_trace_info, async_openai_client):
    set_trace_info()

    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_async_with_token_count",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async_with_token_count(set_trace_info, loop, async_openai_client):
    set_trace_info()
    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_embedding_async_outside_transaction(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_embedding_async_ai_monitoring_disabled(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )
