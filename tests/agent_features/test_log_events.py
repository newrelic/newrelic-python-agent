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
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction


class NonPrintableObject(object):
    def __str__(self):
        raise RuntimeError("Unable to print object.")
    
    __repr__ = __str__


class NonSerializableObject(object):
    def __str__(self):
        return "<%s object>" % self.__class__.__name__

    __repr__ = __str__


def combine_dicts(defaults, overrides):
    combined = defaults.copy()
    combined.update(overrides)
    return combined


def set_trace_ids():
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"


def exercise_record_log_event():
    set_trace_ids()

    record_log_event("no_other_arguments")
    record_log_event("keyword_arguments", timestamp=1234, level="ERROR", attributes={"key": "value"})
    record_log_event("positional_arguments", "WARNING", 2345, {"key": "value"})
    record_log_event("serialized_attributes", attributes=_serialized_attributes)

    # Unsent due to message content missing
    record_log_event("")
    record_log_event("         ")
    record_log_event(None)
    record_log_event(None, attributes={"attributes_only": "value"})


enable_log_forwarding = override_application_settings(
    {"application_logging.forwarding.enabled": True, "application_logging.forwarding.context_data.enabled": True}
)
disable_log_attributes = override_application_settings(
    {"application_logging.forwarding.enabled": True, "application_logging.forwarding.context_data.enabled": False}
)
disable_log_forwarding = override_application_settings({"application_logging.forwarding.enabled": False})

_common_attributes_service_linking = {
    "timestamp": None,
    "hostname": None,
    "entity.name": "Python Agent Test (agent_features)",
    "entity.guid": None,
}
_common_attributes_trace_linking = {"span.id": "abcdefgh", "trace.id": "abcdefgh12345678"}
_common_attributes_trace_linking.update(_common_attributes_service_linking)

_serialized_attributes = {
    "str_attr": "Value",
    "bytes_attr": b"value",
    "int_attr": 1,
    "dict_attr": {"key": "value"},
    "non_serializable_attr": NonSerializableObject(),
    "non_printable_attr": NonPrintableObject(),
}

_exercise_record_log_event_events = [
    {"message": "no_other_arguments", "level": "UNKNOWN"},
    {"message": "keyword_arguments", "level": "ERROR", "timestamp": 1234, "context.key": "value"},
    {"message": "positional_arguments", "level": "WARNING", "timestamp": 2345, "context.key": "value"},
    {
        "message": "serialized_attributes",
        "context.str_attr": "Value",
        "context.bytes_attr": b"value",
        "context.int_attr": "1",
        "context.dict_attr": '{"key":"value"}',
        "context.non_serializable_attr": "<NonSerializableObject object>",
        "context.non_printable_attr": "<unprintable NonPrintableObject object>",
    },
]
_exercise_record_log_event_inside_transaction_events = [
    combine_dicts(_common_attributes_trace_linking, log) for log in _exercise_record_log_event_events
]
_exercise_record_log_event_outside_transaction_events = [
    combine_dicts(_common_attributes_service_linking, log) for log in _exercise_record_log_event_events
]

# Test Log Forwarding

@enable_log_forwarding
def test_record_log_event_inside_transaction():
    @validate_log_events(_exercise_record_log_event_inside_transaction_events)
    @validate_log_event_count(len(_exercise_record_log_event_inside_transaction_events))
    @background_task()
    def test():
        exercise_record_log_event()

    test()


@enable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_outside_transaction():
    @validate_log_events_outside_transaction(_exercise_record_log_event_outside_transaction_events)
    @validate_log_event_count_outside_transaction(len(_exercise_record_log_event_outside_transaction_events))
    def test():
        exercise_record_log_event()

    test()


@enable_log_forwarding
def test_ignored_transaction_logs_not_forwarded():
    @validate_log_event_count(0)
    @background_task()
    def test():
        ignore_transaction()
        exercise_record_log_event()

    test()


# Test Message Truncation

_test_log_event_truncation_events = [{"message": "A" * 32768}]

@enable_log_forwarding
def test_log_event_truncation_inside_transaction():
    @validate_log_events(_test_log_event_truncation_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        record_log_event("A" * 33000)

    test()


@enable_log_forwarding
@reset_core_stats_engine()
def test_log_event_truncation_outside_transaction():
    @validate_log_events_outside_transaction(_test_log_event_truncation_events)
    @validate_log_event_count_outside_transaction(1)
    def test():
        record_log_event("A" * 33000)

    test()


# Test Log Forwarding Settings

@disable_log_forwarding
def test_disabled_record_log_event_inside_transaction():
    @validate_log_event_count(0)
    @background_task()
    def test():
        exercise_record_log_event()

    test()


@disable_log_forwarding
@reset_core_stats_engine()
def test_disabled_record_log_event_outside_transaction():
    @validate_log_event_count_outside_transaction(0)
    def test():
        exercise_record_log_event()

    test()

# Test Log Attribute Settings

@disable_log_attributes
def test_attributes_disabled_inside_transaction():
    @validate_log_events([{"message": "A"}], forgone_attrs=["context.key"])
    @validate_log_event_count(1)
    @background_task()
    def test():
        record_log_event("A", attributes={"key": "value"})

    test()


@disable_log_attributes
@reset_core_stats_engine()
def test_attributes_disabled_outside_transaction():
    @validate_log_events_outside_transaction([{"message": "A"}], forgone_attrs=["context.key"])
    @validate_log_event_count_outside_transaction(1)
    def test():
        record_log_event("A", attributes={"key": "value"})

    test()
