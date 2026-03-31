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

from conftest import GEMINI_VERSION_METRIC
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
            "request.model": "gemini-embedding-001",
            "vendor": "gemini",
            "ingest_source": "Python",
        },
    )
]


@reset_core_stats_engine()
@validate_custom_events(embedding_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_gemini_embedding",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_embedding(exercise_embedding_model, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    exercise_embedding_model(contents="This is an embedding test.", model="gemini-embedding-001")


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_gemini_embedding_no_content",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_embedding_no_content(exercise_embedding_model, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    exercise_embedding_model(contents="This is an embedding test.", model="gemini-embedding-001")


@reset_core_stats_engine()
@override_llm_token_callback_settings(llm_token_count_callback)
@validate_custom_events(add_token_count_to_events(embedding_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_embeddings:test_gemini_embedding_with_token_count",
    scoped_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    rollup_metrics=[("Llm/embedding/Gemini/embed_content", 1)],
    custom_metrics=[(GEMINI_VERSION_METRIC, 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_gemini_embedding_with_token_count(exercise_embedding_model, set_trace_info):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    exercise_embedding_model(contents="This is an embedding test.", model="gemini-embedding-001")


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_gemini_embedding_outside_txn(exercise_embedding_model):
    exercise_embedding_model(contents="This is an embedding test.", model="gemini-embedding-001")


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_gemini_embedding_disabled_ai_monitoring_events(exercise_embedding_model, set_trace_info):
    set_trace_info()
    exercise_embedding_model(contents="This is an embedding test.", model="gemini-embedding-001")
