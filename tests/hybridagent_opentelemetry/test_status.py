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
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes

from newrelic.api.background_task import background_task


def conditional_decorator(decorator, condition):
    def _conditional_decorator(func):
        if not condition:
            return func
        return decorator(func)

    return _conditional_decorator


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
        decorator=validate_error_event_attributes(
            exact_attrs={
                "agent": {},
                "intrinsic": {"error.message": "Test exception message", "error.class": "builtins:ValueError"},
                "user": {"exception.escaped": False},
            }
        ),
        condition=_record_exception,
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
        decorator=validate_error_event_attributes(
            exact_attrs={
                "agent": {},
                "intrinsic": {"error.message": "Test exception message", "error.class": "builtins:ValueError"},
                "user": {"exception.escaped": True},
            }
        ),
        condition=_record_exception,
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
