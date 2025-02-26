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

import pytest
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, ignore_transaction, record_log_event
from newrelic.core.config import _parse_attributes


class NonPrintableObject:
    def __str__(self):
        raise RuntimeError("Unable to print object.")

    __repr__ = __str__


class NonSerializableObject:
    def __str__(self):
        return f"<{self.__class__.__name__} object>"

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
    # Attributes with value None should be dropped.
    record_log_event("keyword_arguments", timestamp=1234, level="ERROR", attributes={"key": "value", "drop-me": None})
    record_log_event("positional_arguments", "WARNING", 2345, {"key": "value"})
    record_log_event("serialized_attributes", attributes=_serialized_attributes)
    record_log_event(None, attributes={"attributes_only": "value"})
    record_log_event({"attributes_only": "value"})
    record_log_event({"message": "dict_message"})
    record_log_event({"message": 123})

    # Unsent due to message content missing
    record_log_event("")
    record_log_event("         ")
    record_log_event(NonPrintableObject())
    record_log_event({"message": ""})
    record_log_event({"message": NonPrintableObject()})
    record_log_event({"filtered_attribute": "should_be_removed"})
    record_log_event(None)


enable_log_forwarding = override_application_settings(
    {
        "application_logging.forwarding.enabled": True,
        "application_logging.forwarding.context_data.enabled": True,
        "application_logging.forwarding.context_data.exclude": ["filtered_attribute"],
    }
)
disable_log_forwarding = override_application_settings({"application_logging.forwarding.enabled": False})

disable_log_attributes = override_application_settings(
    {"application_logging.forwarding.enabled": True, "application_logging.forwarding.context_data.enabled": False}
)

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
    "attr_value_too_long": "*" * 256,
    f"attr_name_too_long_{'*' * 237}": "value",
    f"attr_name_with_prefix_too_long_{'*' * 220}": "value",
}

_exercise_record_log_event_events = [
    {"message": "no_other_arguments", "level": "UNKNOWN"},
    {"message": "keyword_arguments", "level": "ERROR", "timestamp": 1234, "context.key": "value"},
    {"message": "positional_arguments", "level": "WARNING", "timestamp": 2345, "context.key": "value"},
    {
        "message": "serialized_attributes",
        "context.str_attr": "Value",
        "context.bytes_attr": b"value",
        "context.int_attr": 1,
        "context.dict_attr": "{'key': 'value'}",
        "context.non_serializable_attr": "<NonSerializableObject object>",
        "context.attr_value_too_long": "*" * 255,
    },
    {"context.attributes_only": "value"},
    {"message.attributes_only": "value"},
    {"message": "dict_message"},
    {"message": "123"},
]
_exercise_record_log_event_inside_transaction_events = [
    combine_dicts(_common_attributes_trace_linking, log) for log in _exercise_record_log_event_events
]
_exercise_record_log_event_outside_transaction_events = [
    combine_dicts(_common_attributes_service_linking, log) for log in _exercise_record_log_event_events
]
_exercise_record_log_event_forgone_attrs = [
    "context.non_printable_attr",
    "attr_name_too_long_",
    "attr_name_with_prefix_too_long_",
]


# ================================================
# Test Log Forwarding
# ================================================


@enable_log_forwarding
def test_record_log_event_inside_transaction():
    @validate_log_events(
        _exercise_record_log_event_inside_transaction_events, forgone_attrs=_exercise_record_log_event_forgone_attrs
    )
    @validate_log_event_count(len(_exercise_record_log_event_inside_transaction_events))
    @background_task()
    def test():
        exercise_record_log_event()

    test()


@enable_log_forwarding
@reset_core_stats_engine()
def test_record_log_event_outside_transaction():
    @validate_log_events_outside_transaction(
        _exercise_record_log_event_outside_transaction_events, forgone_attrs=_exercise_record_log_event_forgone_attrs
    )
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


# ================================================
# Test Message Truncation
# ================================================


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


# ================================================
# Test Log Forwarding Settings
# ================================================


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


# ================================================
# Test Log Attribute Settings
# ================================================


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


_test_record_log_event_context_attribute_filtering_params = [
    ("", "", "A", True),
    ("", "A", "A", False),
    ("", "A", "B", True),
    ("A B", "*", "A", True),
    ("A B", "*", "B", True),
    ("A B", "*", "C", False),
    ("A B", "C", "A", True),
    ("A B", "C", "C", False),
    ("A B", "B", "A", True),
    ("A B", "B", "B", False),
    ("A", "A *", "A", False),
    ("A", "A *", "B", False),
    ("A*", "", "A", True),
    ("A*", "", "AB", True),
    ("", "A*", "A", False),
    ("", "A*", "B", True),
    ("A*", "AB", "AC", True),
    ("A*", "AB", "AB", False),
    ("AB", "A*", "AB", True),
    ("A*", "AB*", "ACB", True),
    ("A*", "AB*", "ABC", False),
]


@pytest.mark.parametrize("prefix", ("context", "message"))
@pytest.mark.parametrize("include,exclude,attr,expected", _test_record_log_event_context_attribute_filtering_params)
def test_record_log_event_context_attribute_filtering_inside_transaction(include, exclude, attr, expected, prefix):
    if expected:
        expected_event = {"required_attrs": [f"{prefix}.{attr}"]}
    else:
        expected_event = {"forgone_attrs": [f"{prefix}.{attr}"]}

    @override_application_settings(
        {
            "application_logging.forwarding.enabled": True,
            "application_logging.forwarding.context_data.enabled": True,
            "application_logging.forwarding.context_data.include": _parse_attributes(include),
            "application_logging.forwarding.context_data.exclude": _parse_attributes(exclude),
        }
    )
    @validate_log_events(**expected_event)
    @validate_log_event_count(1)
    @background_task()
    def test():
        if prefix == "context":
            record_log_event("A", attributes={attr: 1})
        else:
            record_log_event({"message": "A", attr: 1})

    test()


@pytest.mark.parametrize("prefix", ("context", "message"))
@pytest.mark.parametrize("include,exclude,attr,expected", _test_record_log_event_context_attribute_filtering_params)
@reset_core_stats_engine()
def test_record_log_event_context_attribute_filtering_outside_transaction(include, exclude, attr, expected, prefix):
    if expected:
        expected_event = {"required_attrs": [f"{prefix}.{attr}"]}
    else:
        expected_event = {"forgone_attrs": [f"{prefix}.{attr}"]}

    @override_application_settings(
        {
            "application_logging.forwarding.enabled": True,
            "application_logging.forwarding.context_data.enabled": True,
            "application_logging.forwarding.context_data.include": _parse_attributes(include),
            "application_logging.forwarding.context_data.exclude": _parse_attributes(exclude),
        }
    )
    @validate_log_events_outside_transaction(**expected_event)
    @validate_log_event_count_outside_transaction(1)
    def test():
        if prefix == "context":
            record_log_event("A", attributes={attr: 1})
        else:
            record_log_event({"message": "A", attr: 1})

    test()


_test_record_log_event_linking_attribute_no_filtering_params = [("", ""), ("", "entity.name"), ("", "*")]


@pytest.mark.parametrize("include,exclude", _test_record_log_event_linking_attribute_no_filtering_params)
def test_record_log_event_linking_attribute_no_filtering_inside_transaction(include, exclude):
    attr = "entity.name"

    @override_application_settings(
        {
            "application_logging.forwarding.enabled": True,
            "application_logging.forwarding.context_data.enabled": True,
            "application_logging.forwarding.context_data.include": _parse_attributes(include),
            "application_logging.forwarding.context_data.exclude": _parse_attributes(exclude),
        }
    )
    @validate_log_events(required_attrs=[attr])
    @validate_log_event_count(1)
    @background_task()
    def test():
        record_log_event("A")

    test()


@pytest.mark.parametrize("include,exclude", _test_record_log_event_linking_attribute_no_filtering_params)
@reset_core_stats_engine()
def test_record_log_event_linking_attribute_filtering_outside_transaction(include, exclude):
    attr = "entity.name"

    @override_application_settings(
        {
            "application_logging.forwarding.enabled": True,
            "application_logging.forwarding.context_data.enabled": True,
            "application_logging.forwarding.context_data.include": _parse_attributes(include),
            "application_logging.forwarding.context_data.exclude": _parse_attributes(exclude),
        }
    )
    @validate_log_events_outside_transaction(required_attrs=[attr])
    @validate_log_event_count_outside_transaction(1)
    def test():
        record_log_event("A")

    test()


# ================================================
# Test Log Event Labels Settings
# ================================================


# Add labels setting value in already processed format
TEST_LABELS = {"testlabel1": "A", "testlabel2": "B", "testlabelexclude": "C"}
TEST_LABELS = [{"label_type": k, "label_value": v} for k, v in TEST_LABELS.items()]


@override_application_settings({"labels": TEST_LABELS, "application_logging.forwarding.labels.enabled": True})
@background_task()
def test_label_forwarding_enabled():
    txn = current_transaction()
    session = list(txn.application._agent._applications.values())[0]._active_session

    common = session.get_log_events_common_block()
    # Excluded label should not appear, and other labels should be prefixed with 'tag.'
    assert common == {"tags.testlabel1": "A", "tags.testlabel2": "B", "tags.testlabelexclude": "C"}


@override_application_settings(
    {
        "labels": TEST_LABELS,
        "application_logging.forwarding.labels.enabled": True,
        "application_logging.forwarding.labels.exclude": {"testlabelexclude"},
    }
)
@background_task()
def test_label_forwarding_enabled_exclude():
    txn = current_transaction()
    session = list(txn.application._agent._applications.values())[0]._active_session

    common = session.get_log_events_common_block()
    # Excluded label should not appear, and other labels should be prefixed with 'tags.'
    assert common == {"tags.testlabel1": "A", "tags.testlabel2": "B"}


@override_application_settings({"labels": TEST_LABELS, "application_logging.forwarding.labels.enabled": False})
@background_task()
def test_label_forwarding_disabled():
    txn = current_transaction()
    session = list(txn.application._agent._applications.values())[0]._active_session

    common = session.get_log_events_common_block()
    # No labels should appear
    assert common == {}


# ================================================
# Test Log Event Global Custom Attributes Settings
# ================================================


@override_application_settings(
    {"application_logging.forwarding.custom_attributes": [("custom_attr_1", "value 1"), ("custom_attr_2", "value 2")]}
)
@background_task()
def test_global_custom_attribute_forwarding_enabled():
    txn = current_transaction()
    session = list(txn.application._agent._applications.values())[0]._active_session

    common = session.get_log_events_common_block()
    # Both attrs should appear
    assert common == {"custom_attr_1": "value 1", "custom_attr_2": "value 2"}


@override_application_settings({"application_logging.forwarding.custom_attributes": [("custom_attr_1", "a" * 256)]})
@background_task()
def test_global_custom_attribute_forwarding_truncation():
    txn = current_transaction()
    session = list(txn.application._agent._applications.values())[0]._active_session

    common = session.get_log_events_common_block()
    # Attribute value should be truncated to the max user attribute length
    assert common == {"custom_attr_1": "a" * 255}


@override_application_settings(
    {"application_logging.forwarding.custom_attributes": [(f"custom_attr_{i + 1}", "value") for i in range(129)]}
)
@background_task()
def test_global_custom_attribute_forwarding_max_num_attrs():
    txn = current_transaction()
    session = list(txn.application._agent._applications.values())[0]._active_session

    common = session.get_log_events_common_block()
    # Should be truncated to the max number of user attributes
    assert common == {f"custom_attr_{i + 1}": "value" for i in range(128)}
