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
    override_llm_token_callback_settings,
    reset_core_stats_engine,
    validate_attributes,
)
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
from newrelic.api.transaction import add_custom_attribute

embedding_recorded_events = [
    (
        {"type": "LlmEmbedding"},
        {
            "id": None,  # UUID that varies with each run
            "span_id": None,
            "trace_id": "trace-id",
            "input": "This is an embedding test.",
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "duration": None,  # Response time varies each test run
            "response.model": "text-embedding-ada-002-v2",
            "request.model": "text-embedding-ada-002",
            "request_id": "c70828b2293314366a76a2b1dcb20688",
            "response.organization": "new-relic-nkmd8b",
            "response.headers.llmVersion": "2020-10-01",
            "response.headers.ratelimitLimitRequests": 200,
            "response.headers.ratelimitLimitTokens": 150000,
            "response.headers.ratelimitResetTokens": "2ms",
            "response.headers.ratelimitResetRequests": "19m45.394s",
            "response.headers.ratelimitRemainingTokens": 149994,
            "response.headers.ratelimitRemainingRequests": 197,
            "vendor": "openai",
            "ingest_source": "Python",
        },
    )
]


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_openai_embedding_sync",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync(set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_openai_embedding_sync_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_no_content(set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_openai_embedding_sync_with_token_count",
    scoped_metrics=[("Llm/embedding/OpenAI/create", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/create", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_sync_with_token_count(set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_embedding_sync_outside_txn():
    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_embedding_sync_disabled_ai_monitoring_events(set_trace_info):
    set_trace_info()
    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_openai_embedding_async",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async(loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_openai_embedding_async_no_content",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async_no_content(loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_openai_embedding_async_with_token_count",
    scoped_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    rollup_metrics=[("Llm/embedding/OpenAI/acreate", 1)],
    custom_metrics=[(f"Supportability/Python/ML/OpenAI/{openai.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_openai_embedding_async_with_token_count(loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_openai_embedding_async_outside_transaction(loop):
    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_openai_embedding_async_disabled_ai_monitoring_events(loop):
    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


def test_openai_embedding_functions_marked_as_wrapped_for_sdk_compatibility():
    assert openai.Embedding._nr_wrapped
    assert openai.util.convert_to_openai_object._nr_wrapped
