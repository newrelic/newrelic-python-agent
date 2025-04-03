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
import copy

import pytest

from newrelic.api.transaction import current_transaction
from testing_support.fixtures import override_application_settings

disabled_ai_monitoring_settings = override_application_settings({"ai_monitoring.enabled": False})
disabled_ai_monitoring_streaming_settings = override_application_settings({"ai_monitoring.streaming.enabled": False})
disabled_ai_monitoring_record_content_settings = override_application_settings(
    {"ai_monitoring.record_content.enabled": False}
)


def llm_token_count_callback(model, content):
    return 105


def add_token_count_to_events(expected_events):
    events = copy.deepcopy(expected_events)
    for event in events:
        if event[0]["type"] != "LlmChatCompletionSummary":
            event[1]["token_count"] = 105
    return events


def events_sans_content(event):
    new_event = copy.deepcopy(event)
    for _event in new_event:
        if "input" in _event[1]:
            del _event[1]["input"]
        elif "content" in _event[1]:
            del _event[1]["content"]
    return new_event


def events_sans_llm_metadata(expected_events):
    events = copy.deepcopy(expected_events)
    for event in events:
        del event[1]["llm.conversation_id"], event[1]["llm.foo"]
    return events


def events_with_context_attrs(expected_events):
    events = copy.deepcopy(expected_events)
    for event in events:
        event[1]["llm.context"] = "attr"
    return events


@pytest.fixture(scope="session")
def set_trace_info():
    def _set_trace_info():
        txn = current_transaction()
        if txn:
            txn.guid = "transaction-id"
            txn._trace_id = "trace-id"

    return _set_trace_info
