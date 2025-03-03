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

_common_attributes_service_linking = {
    "timestamp": None,
    "hostname": None,
    "entity.name": "Python Agent Test (logger_structlog)",
    "entity.guid": None,
}

_common_attributes_trace_linking = {
    "span.id": "abcdefgh",
    "trace.id": "abcdefgh12345678",
    **_common_attributes_service_linking,
}


@pytest.fixture(scope="function")
def callsite_parameter_logger(structlog_caplog):
    import structlog

    structlog.configure(
        processors=(
            structlog.processors.CallsiteParameterAdder(
                [structlog.processors.CallsiteParameter.FILENAME, structlog.processors.CallsiteParameter.FUNC_NAME]
            ),
            structlog.processors.KeyValueRenderer(),
        ),
        logger_factory=lambda *args, **kwargs: structlog_caplog,
    )

    _callsite_logger = structlog.get_logger()
    return _callsite_logger


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_inside_transaction(exercise_logging_multiple_lines):
    @validate_log_events(
        [
            {"message": "Cat", "level": "INFO", **_common_attributes_trace_linking},
            {"message": "Dog", "level": "ERROR", **_common_attributes_trace_linking},
            {"message": "Elephant", "level": "CRITICAL", **_common_attributes_trace_linking},
        ]
    )
    @validate_log_event_count(3)
    @background_task()
    def test():
        exercise_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_filtering_inside_transaction(exercise_filtering_logging_multiple_lines):
    @validate_log_events(
        [
            {"message": "Dog", "level": "ERROR", **_common_attributes_trace_linking},
            {"message": "Elephant", "level": "CRITICAL", **_common_attributes_trace_linking},
        ]
    )
    @validate_log_event_count(2)
    @background_task()
    def test():
        exercise_filtering_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_outside_transaction(exercise_logging_multiple_lines):
    @validate_log_events_outside_transaction(
        [
            {"message": "Cat", "level": "INFO", **_common_attributes_service_linking},
            {"message": "Dog", "level": "ERROR", **_common_attributes_service_linking},
            {"message": "Elephant", "level": "CRITICAL", **_common_attributes_service_linking},
        ]
    )
    @validate_log_event_count_outside_transaction(3)
    def test():
        exercise_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_filtering_outside_transaction(exercise_filtering_logging_multiple_lines):
    @validate_log_events_outside_transaction(
        [
            {"message": "Dog", "level": "ERROR", **_common_attributes_service_linking},
            {"message": "Elephant", "level": "CRITICAL", **_common_attributes_service_linking},
        ]
    )
    @validate_log_event_count_outside_transaction(2)
    def test():
        exercise_filtering_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
@validate_log_events(
    [{"message": "event='Dog' filename='test_log_forwarding.py' func_name='test_callsite_processor'", "level": "INFO"}]
)
@validate_log_event_count(1)
@background_task()
def test_callsite_processor(callsite_parameter_logger, structlog_caplog):
    callsite_parameter_logger.msg("Dog")
    assert "Dog" in structlog_caplog.caplog[0]
    assert len(structlog_caplog.caplog) == 1
    assert "filename='test_log_forwarding.py'" in structlog_caplog.caplog[0]
    assert "func_name='test_callsite_processor'" in structlog_caplog.caplog[0]
