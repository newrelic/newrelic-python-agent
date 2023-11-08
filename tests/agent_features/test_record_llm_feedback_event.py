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

from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_events import validate_ml_events

from newrelic.api.background_task import background_task
from newrelic.api.ml_model import record_llm_feedback_event

llm_feedback_all_args_recorded_events = [
    (
        {"type": "LlmFeedbackMessage"},
        {
            "id": None,
            "category": "informative",
            "rating": "1",
            "message_id": "message_id",
            "request_id": "request_id",
            "conversation_id": "conversation_id",
            "ingest_source": "Python",
            "message": "message",
            "metadata": "metadata",
        },
    ),
]


@reset_core_stats_engine()
def test_record_llm_feedback_event_all_args_supplied():
    @validate_ml_events(llm_feedback_all_args_recorded_events)
    @background_task()
    def _test():
        record_llm_feedback_event(
            rating=1,
            message_id="message_id",
            category="informative",
            request_id="request_id",
            conversation_id="conversation_id",
            message="message",
            metadata="metadata",
        )

    _test()


llm_feedback_required_args_recorded_events = [
    (
        {"type": "LlmFeedbackMessage"},
        {
            "id": None,
            "category": "",
            "rating": "1",
            "message_id": "message_id",
            "request_id": "",
            "conversation_id": "",
            "ingest_source": "Python",
            "message": "",
            "metadata": "",
        },
    ),
]


@reset_core_stats_engine()
def test_record_llm_feedback_event_required_args_supplied():
    @validate_ml_events(llm_feedback_required_args_recorded_events)
    @background_task()
    def _test():
        record_llm_feedback_event(message_id="message_id", rating=1)

    _test()


@reset_core_stats_engine()
def test_record_llm_feedback_event_outside_txn():
    @validate_ml_event_count(count=0)
    def _test():
        record_llm_feedback_event(
            rating=1,
            message_id="message_id",
            category="informative",
            request_id="request_id",
            conversation_id="conversation_id",
            message="message",
            metadata="metadata",
        )

    _test()
