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
from opentelemetry.trace.status import Status, StatusCode
from testing_support.fixtures import dt_enabled
from testing_support.util import conditional_decorator
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes

from newrelic.api.background_task import background_task


# `set_status` takes in a status argument that can be either
# a Status or StatusCode type and a description argument.
# Status has a StatusCode attribute and an optional description attribute.
# If current StatusCode is StatusCode.OK, calls to set_status on this span are no-ops.
# If status_to_set is StatusCode.UNSET, this is also a no-op.
@pytest.mark.parametrize(
    "current_status,status_to_set,expected_status_code",
    [
        (Status(StatusCode.UNSET), Status(StatusCode.OK), StatusCode.OK),  # current_status==UNSET -> status_to_set
        (
            Status(StatusCode.UNSET),
            Status(StatusCode.ERROR),
            StatusCode.ERROR,
        ),  # current_status==UNSET -> status_to_set
        (
            Status(StatusCode.OK),
            Status(StatusCode.UNSET),
            StatusCode.OK,
        ),  # current_status==OK -> No-Op / status_to_set==UNSET -> No-Op
        (Status(StatusCode.OK), Status(StatusCode.ERROR), StatusCode.OK),  # current_status==OK -> No-Op
        (Status(StatusCode.ERROR), Status(StatusCode.UNSET), StatusCode.ERROR),  # status_to_set==UNSET -> No-Op
        (Status(StatusCode.ERROR), Status(StatusCode.OK), StatusCode.OK),  # current_status==ERROR -> status_to_set
        (Status(StatusCode.UNSET), StatusCode.OK, StatusCode.OK),  # current_status==UNSET -> status_to_set
        (Status(StatusCode.UNSET), StatusCode.ERROR, StatusCode.ERROR),  # current_status==UNSET -> status_to_set
        (
            Status(StatusCode.OK),
            StatusCode.UNSET,
            StatusCode.OK,
        ),  # current_status==OK -> No-Op / status_to_set==UNSET -> No-Op
        (Status(StatusCode.OK), StatusCode.ERROR, StatusCode.OK),  # current_status==OK -> No-Op
        (Status(StatusCode.ERROR), StatusCode.UNSET, StatusCode.ERROR),  # status_to_set==UNSET -> No-Op
        (Status(StatusCode.ERROR), StatusCode.OK, StatusCode.OK),  # current_status==ERROR -> status_to_set
    ],
    ids=(
        "status_unset_to_ok",
        "status_unset_to_error",
        "status_ok_to_unset",
        "status_ok_to_error",
        "status_error_to_unset",
        "status_error_to_ok",
        "status_code_unset_to_ok",
        "status_code_unset_to_error",
        "status_code_ok_to_unset",
        "status_code_ok_to_error",
        "status_code_error_to_unset",
        "status_code_error_to_ok",
    ),
)
def test_status_setting(tracer, current_status, status_to_set, expected_status_code):
    @background_task()
    def _test():
        with tracer.start_as_current_span(name="TestSpan") as span:
            # First, set to the current status to simulate the initial state
            span.set_status(current_status)

            # Then, attempt to set the new status
            span.set_status(status_to_set)
            assert span.status.status_code == expected_status_code

    _test()


@pytest.mark.parametrize("_record_exception", [True, False])
@pytest.mark.parametrize("_set_status_on_exception", [True, False])
def test_set_status_with_start_as_current_span(tracer, _record_exception, _set_status_on_exception):
    @dt_enabled
    @conditional_decorator(
        condition=_record_exception,
        decorator=validate_error_event_attributes(
            exact_attrs={
                "agent": {},
                "intrinsic": {"error.message": "Test exception message", "error.class": "builtins:ValueError"},
                "user": {"exception.escaped": False},
            }
        ),
    )
    @background_task()
    def _test():
        with pytest.raises(ValueError):
            with tracer.start_as_current_span(
                name="TestSpan", record_exception=_record_exception, set_status_on_exception=_set_status_on_exception
            ) as span:
                raise ValueError("Test exception message")

        assert span.status.status_code == StatusCode.ERROR if _set_status_on_exception else StatusCode.UNSET

    _test()


@pytest.mark.parametrize("_record_exception", [True, False])
@pytest.mark.parametrize("_set_status_on_exception", [True, False])
def test_set_status_with_start_span(tracer, _record_exception, _set_status_on_exception):
    @dt_enabled
    @conditional_decorator(
        condition=_record_exception,
        decorator=validate_error_event_attributes(
            exact_attrs={
                "agent": {},
                "intrinsic": {"error.message": "Test exception message", "error.class": "builtins:ValueError"},
                "user": {"exception.escaped": True},
            }
        ),
    )
    @background_task()
    def _test():
        with pytest.raises(ValueError):
            with tracer.start_span(
                name="TestSpan", record_exception=_record_exception, set_status_on_exception=_set_status_on_exception
            ) as span:
                raise ValueError("Test exception message")

        assert span.status.status_code == StatusCode.ERROR if _set_status_on_exception else StatusCode.UNSET

    _test()


# `set_status` takes in a status argument that can be either
# a Status or StatusCode type and a description argument.
# Status has a StatusCode attribute and an optional description attribute.
# If Status type is passed in, the description argument is ignored.
# If StatusCode type is passed in, the description argument is used to
# create a Status object.
# Only StatusCode.ERROR should have a description, so if StatusCode.OK is passed
# in with a description, the description will be ignored within the Status object.
@pytest.mark.parametrize(
    "status_to_set,description,expected_status_code",
    [
        (Status(StatusCode.OK), None, StatusCode.OK),  # OK_Status_no_description, no description
        (
            Status(StatusCode.OK),
            "I will be ignored in set_status",
            StatusCode.OK,
        ),  # OK_Status_no_description, description
        (
            Status(StatusCode.OK, "I will be ignored in Status"),
            None,
            StatusCode.OK,
        ),  # OK_Status_with_description, no description
        (
            Status(StatusCode.OK, "I will be ignored in Status"),
            "I will be ignored in set_status",
            StatusCode.OK,
        ),  # OK_Status_with_description, description
        (Status(StatusCode.ERROR), None, StatusCode.ERROR),  # Error_Status_no_description, no description
        (
            Status(StatusCode.ERROR),
            "I will be ignored in set_status",
            StatusCode.ERROR,
        ),  # Error_Status_no_description, description
        (
            Status(StatusCode.ERROR, "This is where I belong"),
            None,
            StatusCode.ERROR,
        ),  # Error_Status_with_description, no description
        (
            Status(StatusCode.ERROR, "This is where I belong"),
            "I will be ignored in set_status",
            StatusCode.ERROR,
        ),  # Error_Status_with_description, description
        (StatusCode.OK, None, StatusCode.OK),  # OK_StatusCode, no description
        (StatusCode.OK, "I will be ignored in Status", StatusCode.OK),  # OK_StatusCode, description
        (StatusCode.ERROR, None, StatusCode.ERROR),  # Error_StatusCode, no description
        (StatusCode.ERROR, "This is where I belong", StatusCode.ERROR),  # Error_StatusCode, description
    ],
    ids=(
        "ok_status_no_description-no_description",
        "ok_status_no_description-description",
        "ok_status_description-no_description",
        "ok_status_description-description",
        "error_status_no_description-no_description",
        "error_status_no_description-description",
        "error_status_description-no_description",
        "error_status_description-description",
        "ok_status_code-no_description",
        "ok_status_code-description",
        "error_status_code-no_description",
        "error_status_code-description",
    ),
)
def test_status_setting(tracer, status_to_set, description, expected_status_code):
    @background_task()
    def _test():
        with tracer.start_as_current_span(name="TestSpan") as span:
            # Set the new status
            span.set_status(status_to_set, description)

            # If status code is OK, do not have description
            # if expected_status_code == StatusCode.OK:
            if span.status.status_code == StatusCode.OK:
                assert span.status.description is None

            # If status code is ERROR, make sure description
            # is set correctly (if provided):
            if span.status.status_code == StatusCode.ERROR:
                assert span.status.description in [None, "This is where I belong"]

    _test()
