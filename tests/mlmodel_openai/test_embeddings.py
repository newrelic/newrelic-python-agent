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
from testing_support.fixtures import (  # function_not_called,; override_application_settings,
    function_not_called,
    override_application_settings,
    reset_core_stats_engine,
)

from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, add_custom_attribute
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_event_payload import (
    validate_ml_event_payload,
)
from testing_support.validators.validate_ml_events import validate_ml_events
from testing_support.validators.validate_ml_events_outside_transaction import (
    validate_ml_events_outside_transaction,
)
import newrelic.core.otlp_utils
from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_ml_event
from newrelic.core.config import global_settings
from newrelic.packages import six


def set_trace_info():
    txn = current_transaction()
    if txn:
        txn._trace_id = "trace-id"
    trace = current_trace()
    if trace:
        trace.guid = "span-id"


sync_embedding_recorded_events = [
    (
        {'type': 'LlmEmbedding'},
        {
            'id': None,  # UUID that varies with each run
            'appName': 'Python Agent Test (mlmodel_openai)',
            'transaction_id': None,
            'span_id': "span-id",
            'trace_id': "trace-id",
            "input": "This is an embedding test.",
            'api_key_last_four_digits': 'sk-CRET',
            'duration': None,  # Response time varies each test run
            'response.model': 'text-embedding-ada-002-v2',
            'request.model': 'text-embedding-ada-002',
            'request_id': "c70828b2293314366a76a2b1dcb20688",
            'response.organization': 'new-relic-nkmd8b',
            'response.usage.total_tokens': 6,
            'response.usage.prompt_tokens': 6,
            'response.api_type': 'None',
            'response.headers.llmVersion': '2020-10-01',
            'response.headers.ratelimitLimitRequests': 200,
            'response.headers.ratelimitLimitTokens': 150000,
            'response.headers.ratelimitResetTokens': '2ms',
            'response.headers.ratelimitResetRequests': '19m45.394s',
            'response.headers.ratelimitRemainingTokens': 149994,
            'response.headers.ratelimitRemainingRequests': 197,
            'vendor': 'openAI',
        },
    ),
]


@reset_core_stats_engine()
@validate_ml_events(sync_embedding_recorded_events)
@validate_ml_event_count(count=1)
@background_task()
def test_openai_embedding_sync():
    set_trace_info()
    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_embedding_sync_outside_txn():
    set_trace_info()
    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


disabled_ml_insights_settings = {"ml_insights_events.enabled": False}


@override_application_settings(disabled_ml_insights_settings)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_chat_completion_sync_disabled_settings():
    set_trace_info()
    set_trace_info()
    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


def test_openai_embedding_async(loop):
    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )
