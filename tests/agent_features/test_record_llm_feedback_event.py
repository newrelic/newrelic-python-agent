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

from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events

from newrelic.api.background_task import background_task
from newrelic.api.ml_model import record_llm_feedback_event


@reset_core_stats_engine()
def test_record_llm_feedback_event_all_args_supplied():
    llm_feedback_all_args_recorded_events = [
        (
            {"type": "LlmFeedbackMessage"},
            {
                "id": None,
                "category": "informative",
                "rating": 1,
                "message_id": "message_id",
                "request_id": "request_id",
                "conversation_id": "conversation_id",
                "ingest_source": "Python",
                "message": "message",
                "foo": "bar",
            },
        ),
    ]

    @validate_custom_events(llm_feedback_all_args_recorded_events)
    @background_task()
    def _test():
        record_llm_feedback_event(
            rating=1,
            message_id="message_id",
            category="informative",
            request_id="request_id",
            conversation_id="conversation_id",
            message="message",
            metadata={"foo": "bar", "message": "custom-message"},
        )

    _test()


@reset_core_stats_engine()
def test_record_llm_feedback_event_required_args_supplied():
    llm_feedback_required_args_recorded_events = [
        (
            {"type": "LlmFeedbackMessage"},
            {
                "id": None,
                "category": "",
                "rating": "Good",
                "message_id": "message_id",
                "request_id": "",
                "conversation_id": "",
                "ingest_source": "Python",
                "message": "",
            },
        ),
    ]

    @validate_custom_events(llm_feedback_required_args_recorded_events)
    @background_task()
    def _test():
        record_llm_feedback_event(message_id="message_id", rating="Good")

    _test()


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_record_llm_feedback_event_outside_txn():
    record_llm_feedback_event(
        rating="Good",
        message_id="message_id",
        category="informative",
        request_id="request_id",
        conversation_id="conversation_id",
        message="message",
        metadata={"foo": "bar"},
    )
