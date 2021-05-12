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

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.api.application import application_instance

from newrelic.common.object_names import callable_name

from testing_support.fixtures import (
    validate_transaction_errors,
    override_application_settings,
    validate_error_event_sample_data,
    validate_transaction_metrics,
    validate_transaction_error_event_count,
)


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
combined_runtime_error_settings = {}
combined_runtime_error_settings.update(expected_runtime_error_settings)
combined_runtime_error_settings.update(ignore_runtime_error_settings)

# Status code settings
expected_status_code_settings = {"error_collector.expected_status_codes": [429]}
ignore_status_code_settings = {"error_collector.ignore_status_codes": [429]}
combined_status_code_settings = {}
combined_status_code_settings.update(expected_runtime_error_settings)
combined_status_code_settings.update(ignore_runtime_error_settings)

_test_record_exception = [(_runtime_error_name, _error_message)]
_intrinsic_attributes = {
    "error.class": _runtime_error_name,
    "error.message": _error_message,
    "error.expected": False,
    "transactionName": "OtherTransaction/Function/test",
}
_metrics_normal = [
    ("Errors/all", 1),
    ("Errors/OtherTransaction/Function/test", 1),
    ("Errors/allOther", 1),
]


# =============== Test ignored/expected classes within transaction ===============

settings_matrix = [
    ({}, False, False),
    (ignore_runtime_error_settings, False, True),
    (expected_runtime_error_settings, True, False),
    (combined_runtime_error_settings, False, True),
]
override_expected_matrix = (True, False, None)

def exercise(override_expected=None, status_code=None):
    try:
        raise RuntimeError(_error_message)
    except RuntimeError:
        if current_transaction() is not None:
            # Record exception inside transaction
            notice_error(expected=override_expected, status_code=status_code)
        else:
            # Record exception outside context of transaction
            application_instance().notice_error(expected=override_expected, status_code=status_code)

@pytest.mark.parametrize("settings,expected,ignore", settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_classes_error_event(settings, expected, ignore, override_expected):
    expected = override_expected if override_expected is not None else expected

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0
    errors = _test_record_exception if not ignore else []

    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    @override_application_settings(settings)
    def _test():
        exercise(override_expected)

    _test()

# =============== Test ignored/expected classes outside transaction ===============

@pytest.mark.parametrize("settings,expected,ignore", settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_classes_error_event_outside_transaction(settings, expected, ignore, override_expected):
    expected = override_expected if override_expected is not None else expected

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0

    @validate_transaction_error_event_count(num_errors=0)  # No transaction, should be 0
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @override_application_settings(settings)
    def _test():
        exercise(override_expected)

    _test()

# =============== Test metrics not incremented ===============

@pytest.mark.skip()
@pytest.mark.parametrize("settings,expected,ignore", settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
def test_classes_exception_metrics(settings, expected, ignore, override_expected):
    expected = override_expected or expected
    metrics = _metrics_normal if not (expected or ignore) else []

    @override_application_settings(settings)
    @validate_transaction_metrics("test", background_task=True, rollup_metrics=metrics)
    @background_task(name="test")
    def _test():
        exercise(override_expected)

    _test()

# =============== Test ignored/expected status codes ===============

class TeapotError(RuntimeError):
    status_code = 429

_teapot_error_name = callable_name(TeapotError)

def retrieve_status_code(exc, value, tb):
    return value.status_code

settings_matrix = [
    ({}, False, False),
    (ignore_status_code_settings, False, True),
    (expected_status_code_settings, True, False),
    (combined_status_code_settings, False, True),
]

status_code_matrix = [None, 429, retrieve_status_code]

@pytest.mark.parametrize("settings,expected,ignore", settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
@pytest.mark.parametrize("status_code", status_code_matrix)
def test_status_codes(settings, expected, ignore, override_expected, status_code):
    expected = override_expected if override_expected is not None else expected
    
    if status_code is None:
        # Override all settings
        ignore = False
        expected = False

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0

    @validate_transaction_error_event_count(num_errors=0)  # No transaction, should be 0
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @override_application_settings(settings)
    def _test():
        try:
            raise TeapotError("I'm a teapot.")
        except:
            notice_error(expected=override_expected, status_code=status_code)

    _test()

# =============== Test mixed ignored and expected settings ===============

ignore_status_code_expected_class_settings = {}
ignore_status_code_expected_class_settings.update(ignore_status_code_settings)
ignore_status_code_expected_class_settings.update(expected_runtime_error_settings)
expected_status_code_ignore_class_settings = {}
expected_status_code_ignore_class_settings.update(expected_status_code_settings)
expected_status_code_ignore_class_settings.update(ignore_runtime_error_settings)

settings_matrix = [
    ({}, False, False),
    (ignore_status_code_expected_class_settings, False, True),
    (expected_status_code_ignore_class_settings, False, True),
]
override_expected_matrix = (True, False, None)
override_ignore_matrix = (True, False, None)

@pytest.mark.parametrize("settings,expected,ignore", settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
@pytest.mark.parametrize("override_ignore", override_ignore_matrix)
def test_mixed_ignore_expected_settings_inside_transaction(settings, expected, ignore, override_expected, override_ignore):
    expected = override_expected if override_expected is not None else expected
    ignore = override_ignore if override_ignore is not None else ignore

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0
    errors = _test_record_exception if not ignore else []

    @validate_transaction_errors(errors=errors)
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @background_task(name="test")
    @override_application_settings(settings)
    def _test():
        exercise(override_expected=override_expected, status_code=429)

    _test()




@pytest.mark.parametrize("settings,expected,ignore", settings_matrix)
@pytest.mark.parametrize("override_expected", override_expected_matrix)
@pytest.mark.parametrize("override_ignore", override_ignore_matrix)
def test_mixed_ignore_expected_settings_outside_transaction(settings, expected, ignore, override_expected, override_ignore):
    expected = override_expected if override_expected is not None else expected
    ignore = override_ignore if override_ignore is not None else ignore

    # Update attributes with parameters
    attributes = _intrinsic_attributes.copy()
    attributes["error.expected"] = expected

    error_count = 1 if not ignore else 0

    @validate_transaction_error_event_count(num_errors=0)  # No transaction, should be 0
    @validate_error_event_sample_data(
        required_attrs=attributes,
        required_user_attrs=False,
        num_errors=error_count,
    )
    @override_application_settings(settings)
    def _test():
        exercise(override_expected)

    _test()
