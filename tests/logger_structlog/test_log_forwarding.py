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
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import \
    validate_log_event_count_outside_transaction
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction


_common_attributes_service_linking = {"timestamp": None, "hostname": None,
                                      "entity.name": "Python Agent Test (logger_structlog)", "entity.guid": None}

_common_attributes_trace_linking = {"span.id": "abcdefgh", "trace.id": "abcdefgh12345678",
                                    **_common_attributes_service_linking}


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_inside_transaction(exercise_logging_multiple_lines):
    @validate_log_events([
        {"message": "Cat", "level": "INFO", **_common_attributes_trace_linking},
        {"message": "Dog", "level": "ERROR", **_common_attributes_trace_linking},
        {"message": "Elephant", "level": "CRITICAL", **_common_attributes_trace_linking},
    ])
    @validate_log_event_count(3)
    @background_task()
    def test():
        exercise_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_filtering_inside_transaction(exercise_filtering_logging_multiple_lines):
    @validate_log_events([
        {"message": "Dog", "level": "ERROR", **_common_attributes_trace_linking},
        {"message": "Elephant", "level": "CRITICAL", **_common_attributes_trace_linking},
    ])
    @validate_log_event_count(2)
    @background_task()
    def test():
        exercise_filtering_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_outside_transaction(exercise_logging_multiple_lines):
    @validate_log_events_outside_transaction([
        {"message": "Cat", "level": "INFO", **_common_attributes_service_linking},
        {"message": "Dog", "level": "ERROR", **_common_attributes_service_linking},
        {"message": "Elephant", "level": "CRITICAL", **_common_attributes_service_linking},
    ])
    @validate_log_event_count_outside_transaction(3)
    def test():
        exercise_logging_multiple_lines()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_logging_filtering_outside_transaction(exercise_filtering_logging_multiple_lines):
    @validate_log_events_outside_transaction([
        {"message": "Dog", "level": "ERROR", **_common_attributes_service_linking},
        {"message": "Elephant", "level": "CRITICAL", **_common_attributes_service_linking},
    ])
    @validate_log_event_count_outside_transaction(2)
    def test():
        exercise_filtering_logging_multiple_lines()

    test()
