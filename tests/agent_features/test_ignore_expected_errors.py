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
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
    validate_error_event_attributes_outside_transaction,
    validate_error_event_sample_data,
    validate_error_trace_attributes_outside_transaction,
    validate_time_metrics_outside_transaction,
    validate_transaction_error_trace_attributes,
    validate_transaction_errors,
    validate_transaction_metrics,
)

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name

_runtime_error_name = callable_name(RuntimeError)
_error_message = "Test error message."

# Settings presets

# Error classes settings
expected_runtime_error_settings = {
    "error_collector.expected_classes": [_runtime_error_name]
}
ignore_runtime_error_settings = {
    "error_collector.ignore_classes": [_runtime_error_name]
}

# Status code settings
expected_status_code_settings = {"error_collector.expected_status_codes": [418]}
ignore_status_code_settings = {"error_collector.ignore_status_codes": [418]}

_test_runtime_error = [(_runtime_error_name, _error_message)]
_intrinsic_attributes = {
    "error.class": _runtime_error_name,
    "error.message": _error_message,
    "error.expected": False,
    "transactionName": "OtherTransaction/Function/test",
}

# =============== Test ignored/expected classes ===============

classes_settings_matrix = [
    ({}, False, False),
    (ignore_runtime_error_settings, False, True),
    (expected_runtime_error_settings, True, False),
]
override_expected_matrix = (True, False, None)


def exercise(expected=None, ignore=None, status_code=None, application=None):
    try:
        raise RuntimeError(_error_message)
    except RuntimeError:
        if current_transaction() is None:
            # Record exception inside transaction
            application = application or application_instance()

        notice_error(
            expected=expected,
            ignore=ignore,
            status_code=status_code,
            application=application,
        )


@pytest.mark.parametrize("settings,expected,ignore", classes_settings_matrix)
def test_classes_error_event_inside_transaction(settings, expected, ignore):
    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0
    errors = _test_runtime_error if not ignore else []

    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    @override_application_settings(settings)
    def _test():
        exercise()

    _test()


@pytest.mark.parametrize("settings,expected,ignore", classes_settings_matrix)
def test_classes_error_event_outside_transaction(settings, expected, ignore):
    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected
    attributes["transactionName"] = None

    error_count = 1 if not ignore else 0

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        exact_attrs={"intrinsic": attributes, "agent": {}, "user": {}},
        num_errors=error_count,
    )
    @override_application_settings(settings)
    def _test():
        exercise()

    _test()


# =============== Test error trace attributes ===============
# Override testing is required to ensure the proper handling of
# overrides. First attempt at implementation did not correctly handle this
# and resulted in discrepancies between error events and traced errors.


error_trace_settings_matrix = [
    ({}, False),
    (expected_runtime_error_settings, True),
]
override_expected_matrix = (True, False, None)


@pytest.mark.parametrize("settings,expected", error_trace_settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_error_trace_attributes_inside_transaction(
    settings, expected, override_expected
):
    expected = override_expected if override_expected is not None else expected

    error_trace_attributes = {
        "intrinsic": {
            "error.expected": expected,
        },
        "agent": {},
        "user": {},
    }

    @validate_transaction_error_trace_attributes(exact_attrs=error_trace_attributes)
    @background_task(name="test")
    @override_application_settings(settings)
    def _test():
        exercise(override_expected)

    _test()


@pytest.mark.parametrize("settings,expected", error_trace_settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_error_trace_attributes_outside_transaction(
    settings, expected, override_expected
):
    expected = override_expected if override_expected is not None else expected

    error_trace_attributes = {
        "intrinsic": {
            "error.class": _runtime_error_name,
            "error.message": _error_message,
            "error.expected": expected,
            "transactionName": None,
        },
        "agent": {},
        "user": {},
    }

    @reset_core_stats_engine()
    @validate_error_trace_attributes_outside_transaction(
        _runtime_error_name, exact_attrs=error_trace_attributes
    )
    @override_application_settings(settings)
    def _test():
        exercise(override_expected)

    _test()


# =============== Test metrics not incremented ===============


@pytest.mark.parametrize("expected", override_expected_matrix)
def test_error_metrics_inside_transaction(expected):
    normal_metrics_count = None if expected else 1
    expected_metrics_count = 1 if expected else None
    metrics_payload = [
        ("Errors/all", normal_metrics_count),
        ("Errors/OtherTransaction/Function/test", normal_metrics_count),
        ("Errors/allOther", normal_metrics_count),
        ("ErrorsExpected/all", expected_metrics_count),
    ]

    @validate_transaction_metrics(
        "test", background_task=True, rollup_metrics=metrics_payload
    )
    @background_task(name="test")
    def _test():
        exercise(expected)

    _test()


@pytest.mark.parametrize("expected", override_expected_matrix)
def test_error_metrics_outside_transaction(expected):
    normal_metrics_count = None if expected else 1
    expected_metrics_count = 1 if expected else None
    metrics_payload = [
        ("Errors/all", normal_metrics_count),
        ("ErrorsExpected/all", expected_metrics_count),
    ]

    @reset_core_stats_engine()
    @validate_time_metrics_outside_transaction(metrics_payload)
    def _test():
        exercise(expected)

    _test()


# =============== Test ignored/expected status codes ===============


class TeapotError(RuntimeError):
    status_code = 418


_teapot_error_name = callable_name(TeapotError)
_test_teapot_error = [(_teapot_error_name, _error_message)]


def retrieve_status_code(exc, value, tb):
    return value.status_code


status_codes_settings_matrix = [
    ({}, False, False),
    (ignore_status_code_settings, False, True),
    (expected_status_code_settings, True, False),
]

status_code_matrix = [None, 418, retrieve_status_code]


@pytest.mark.parametrize("settings,expected,ignore", status_codes_settings_matrix)
@pytest.mark.parametrize("status_code", status_code_matrix)
def test_status_codes_inside_transaction(settings, expected, ignore, status_code):
    if status_code is None:
        # Override all settings
        ignore = False
        expected = False

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected
    attributes["error.class"] = _teapot_error_name

    error_count = 1 if not ignore else 0
    errors = _test_teapot_error if not ignore else []

    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    @override_application_settings(settings)
    def _test():
        try:
            raise TeapotError(_error_message)
        except:
            notice_error(status_code=status_code)

    _test()


@pytest.mark.parametrize("settings,expected,ignore", status_codes_settings_matrix)
@pytest.mark.parametrize("status_code", status_code_matrix)
def test_status_codes_outside_transaction(settings, expected, ignore, status_code):
    if status_code is None:
        # Override all settings
        ignore = False
        expected = False

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected
    attributes["error.class"] = _teapot_error_name
    attributes["transactionName"] = None

    error_count = 1 if not ignore else 0

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        exact_attrs={"intrinsic": attributes, "agent": {}, "user": {}},
        num_errors=error_count,
    )
    @override_application_settings(settings)
    def _test():
        try:
            raise TeapotError(_error_message)
        except:
            notice_error(status_code=status_code)

    _test()


# =============== Test mixed ignored and expected settings ===============

# Aggregate settings
ignore_status_code_expected_class_settings = {}
ignore_status_code_expected_class_settings.update(ignore_status_code_settings)
ignore_status_code_expected_class_settings.update(expected_runtime_error_settings)
expected_status_code_ignore_class_settings = {}
expected_status_code_ignore_class_settings.update(expected_status_code_settings)
expected_status_code_ignore_class_settings.update(ignore_runtime_error_settings)
combined_runtime_error_settings = {}
combined_runtime_error_settings.update(expected_runtime_error_settings)
combined_runtime_error_settings.update(ignore_runtime_error_settings)
combined_status_code_settings = {}
combined_status_code_settings.update(expected_status_code_settings)
combined_status_code_settings.update(ignore_status_code_settings)

mixed_settings_matrix = [
    ({}, False, False),
    (ignore_status_code_expected_class_settings, True, True),
    (expected_status_code_ignore_class_settings, True, True),
    (combined_runtime_error_settings, True, True),
    (combined_status_code_settings, True, True),
]
override_expected_matrix = (True, False, None)
override_ignore_matrix = (True, False, None)


@pytest.mark.parametrize("settings,expected,ignore", mixed_settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
@pytest.mark.parametrize("override_ignore", override_ignore_matrix)
def test_mixed_ignore_expected_settings_inside_transaction(
    settings, expected, ignore, override_expected, override_ignore
):
    expected = override_expected if override_expected is not None else expected
    ignore = override_ignore if override_ignore is not None else ignore

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0
    errors = _test_runtime_error if not ignore else []

    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    @override_application_settings(settings)
    def _test():
        exercise(override_expected, override_ignore, status_code=418)

    _test()


@pytest.mark.parametrize("settings,expected,ignore", mixed_settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
@pytest.mark.parametrize("override_ignore", override_ignore_matrix)
def test_mixed_ignore_expected_settings_outside_transaction(
    settings, expected, ignore, override_expected, override_ignore
):
    expected = override_expected if override_expected is not None else expected
    ignore = override_ignore if override_ignore is not None else ignore

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected
    attributes["transactionName"] = None

    error_count = 1 if not ignore else 0

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        exact_attrs={"intrinsic": attributes, "agent": {}, "user": {}},
        num_errors=error_count,
    )
    @override_application_settings(settings)
    def _test():
        exercise(override_expected, override_ignore, status_code=418)

    _test()


# =============== Test multiple override types ===============

override_matrix = (
    (True, True),
    (False, False),
    (lambda e, v, t: True, True),
    (lambda e, v, t: False, False),
    ([_runtime_error_name], True),
    ([], False),
    (None, False),
)


@pytest.mark.parametrize("override,result", override_matrix)
@pytest.mark.parametrize("parameter", ("ignore", "expected"))
def test_overrides_inside_transaction(override, result, parameter):
    ignore = result if parameter == "ignore" else False
    expected = result if parameter == "expected" else False
    kwargs = {parameter: override}

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0
    errors = _test_runtime_error if not ignore else []

    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    def _test():
        exercise(**kwargs)

    _test()


@pytest.mark.parametrize("override,result", override_matrix)
@pytest.mark.parametrize("parameter", ("ignore", "expected"))
def test_overrides_outside_transaction(override, result, parameter):
    ignore = result if parameter == "ignore" else False
    expected = result if parameter == "expected" else False
    kwargs = {parameter: override}

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected
    attributes["transactionName"] = None

    error_count = 1 if not ignore else 0

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        exact_attrs={"intrinsic": attributes, "agent": {}, "user": {}},
        num_errors=error_count,
    )
    def _test():
        exercise(**kwargs)

    _test()
