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

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, record_log_event, ignore_transaction
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import validate_log_event_count_outside_transaction
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction


def set_trace_ids():
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"


def exercise_record_log_event(message="A"):
    set_trace_ids()

    record_log_event(message, "ERROR")

enable_log_forwarding = override_application_settings({"application_logging.forwarding.enabled": True})
disable_log_forwarding = override_application_settings({"application_logging.forwarding.enabled": False})

_common_attributes_service_linking = {"timestamp": None, "hostname": None, "entity.name": "Python Agent Test (agent_features)", "entity.guid": None}
_common_attributes_trace_linking = {"span.id": "abcdefgh", "trace.id": "abcdefgh12345678"}
_common_attributes_trace_linking.update(_common_attributes_service_linking)
_test_record_log_event_inside_transaction_events = [{"message": "A", "level": "ERROR"}]
_test_record_log_event_inside_transaction_events[0].update(_common_attributes_trace_linking)

@enable_log_forwarding
def test_record_log_event_inside_transaction():
    @validate_log_events(_test_record_log_event_inside_transaction_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_record_log_event()
    
    test()


_test_record_log_event_outside_transaction_events = [{"message": "A", "level": "ERROR"}]
_test_record_log_event_outside_transaction_events[0].update(_common_attributes_service_linking)

@enable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_outside_transaction():
    @validate_log_events_outside_transaction(_test_record_log_event_outside_transaction_events)
    @validate_log_event_count_outside_transaction(1)
    def test():
        exercise_record_log_event()

    test()


_test_record_log_event_unknown_level_inside_transaction_events = [{"message": "A", "level": "UNKNOWN"}]
_test_record_log_event_unknown_level_inside_transaction_events[0].update(_common_attributes_trace_linking)

@enable_log_forwarding
def test_record_log_event_unknown_level_inside_transaction():
    @validate_log_events(_test_record_log_event_unknown_level_inside_transaction_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        set_trace_ids()
        record_log_event("A")
    
    test()


_test_record_log_event_unknown_level_outside_transaction_events = [{"message": "A", "level": "UNKNOWN"}]
_test_record_log_event_unknown_level_outside_transaction_events[0].update(_common_attributes_service_linking)

@enable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_unknown_level_outside_transaction():
    @validate_log_events_outside_transaction(_test_record_log_event_unknown_level_outside_transaction_events)
    @validate_log_event_count_outside_transaction(1)
    def test():
        set_trace_ids()
        record_log_event("A")

    test()


@enable_log_forwarding
def test_record_log_event_empty_message_inside_transaction():
    @validate_log_event_count(0)
    @background_task()
    def test():
        exercise_record_log_event("")
    
    test()


@enable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_empty_message_outside_transaction():
    @validate_log_event_count_outside_transaction(0)
    def test():
        exercise_record_log_event("")

    test()


@enable_log_forwarding
def test_record_log_event_whitespace_inside_transaction():
    @validate_log_event_count(0)
    @background_task()
    def test():
        exercise_record_log_event("         ")

    test()


@enable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_whitespace_outside_transaction():
    @validate_log_event_count_outside_transaction(0)
    def test():
        exercise_record_log_event("         ")

    test()


@enable_log_forwarding
def test_ignored_transaction_logs_not_forwarded():
    @validate_log_event_count(0)
    @background_task()
    def test():
        ignore_transaction()
        exercise_record_log_event()

    test()


_test_log_event_truncation_events = [{"message": "A" * 32768, "level": "ERROR"}]
_test_log_event_truncation_events[0].update(_common_attributes_trace_linking)

@enable_log_forwarding
def test_log_event_truncation():
    @validate_log_events(_test_log_event_truncation_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_record_log_event("A" * 33000)

    test()


@disable_log_forwarding
def test_record_log_event_inside_transaction():
    @validate_log_event_count(0)
    @background_task()
    def test():
        exercise_record_log_event()
    
    test()


@disable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_outside_transaction():
    @validate_log_event_count_outside_transaction(0)
    def test():
        exercise_record_log_event()

    test()
