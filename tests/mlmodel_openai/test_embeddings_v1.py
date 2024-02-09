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
from testing_support.fixtures import (  # override_application_settings,
    override_application_settings,
    reset_core_stats_engine,
    validate_custom_event_count,
    validate_attributes,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

disabled_custom_insights_settings = {"custom_insights_events.enabled": False}

embedding_recorded_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_openai)",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "This is an embedding test.",
            "api_key_last_four_digits": "sk-CRET",
            "duration": None,  # Response time varies each test run
            "response.model": "text-embedding-ada-002-v2",
            "request.model": "text-embedding-ada-002",
            "request_id": "fef7adee5adcfb03c083961bdce4f6a4",
            "response.organization": "foobar-jtbczk",
            "response.usage.total_tokens": 6,
            "response.usage.prompt_tokens": 6,
            "response.api_type": "",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 200,
            "response.headers.ratelimitLimitTokens": 150000,
            "response.headers.ratelimitResetTokens": "2ms",
            "response.headers.ratelimitResetRequests": "19m5.228s",
            "response.headers.ratelimitRemainingTokens": 149993,
            "response.headers.ratelimitRemainingRequests": 197,
            "vendor": "openAI",
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
@validate_custom_event_count(count=0)
def test_openai_embedding_sync_outside_txn(sync_openai_client):
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")


@override_application_settings(disabled_custom_insights_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_sync_disabled_settings",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_openai_embedding_sync_disabled_settings(set_trace_info, sync_openai_client):
    set_trace_info()
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
@validate_custom_event_count(count=0)
def test_openai_embedding_async_outside_transaction(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@override_application_settings(disabled_custom_insights_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_embeddings_v1:test_openai_embedding_async_disabled_custom_insights_events",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[
        ("Supportability/Python/ML/OpenAI/%s" % openai.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_openai_embedding_async_disabled_custom_insights_events(loop, async_openai_client):
    loop.run_until_complete(
        async_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
    )
