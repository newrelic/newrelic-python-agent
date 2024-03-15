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
from conftest import (  # pylint: disable=E0611
    add_token_count_to_event,
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_sans_content,
    llm_token_count_callback,
)
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_attributes,
    validate_custom_event_count,
    override_llm_token_callback_settings,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

embedding_recorded_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "This is an embedding test.",
            "duration": None,  # Response time varies each test run
            "response.model": "text-embedding-ada-002-v2",
            "request.model": "text-embedding-ada-002",
            "request_id": "fef7adee5adcfb03c083961bdce4f6a4",
            "response.organization": "foobar-jtbczk",
            "response.usage.total_tokens": 6,
            "response.usage.prompt_tokens": 6,
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 200,
            "response.headers.ratelimitLimitTokens": 150000,
            "response.headers.ratelimitResetTokens": "2ms",
            "response.headers.ratelimitResetRequests": "19m5.228s",
            "response.headers.ratelimitRemainingTokens": 149993,
            "response.headers.ratelimitRemainingRequests": 197,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_no_content(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_event(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_with_token_count",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
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
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
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
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_async_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
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
@validate_custom_events(add_token_count_to_event(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_with_token_count_async",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_with_token_count_async(set_trace_info, loop, async_openai_client):
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
