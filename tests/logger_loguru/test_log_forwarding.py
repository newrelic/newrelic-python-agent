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

import logging

import pytest
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction


def set_trace_ids():
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"


def exercise_logging(logger):
    set_trace_ids()

    logger.warning("C")
    logger.error("D")
    logger.critical("E")

    assert len(logger.caplog.records) == 3


_common_attributes_service_linking = {
    "timestamp": None,
    "hostname": None,
    "entity.name": "Python Agent Test (logger_loguru)",
    "entity.guid": None,
}
_common_attributes_trace_linking = {
    "span.id": "abcdefgh",
    "trace.id": "abcdefgh12345678",
    **_common_attributes_service_linking,
}

_test_logging_inside_transaction_events = [
    {"message": "C", "level": "WARNING", **_common_attributes_trace_linking},
    {"message": "D", "level": "ERROR", **_common_attributes_trace_linking},
    {"message": "E", "level": "CRITICAL", **_common_attributes_trace_linking},
]


@reset_core_stats_engine()
def test_logging_inside_transaction(logger):
    @validate_log_events(_test_logging_inside_transaction_events)
    @validate_log_event_count(3)
    @background_task()
    def test():
        exercise_logging(logger)

    test()


_test_logging_outside_transaction_events = [
    {"message": "C", "level": "WARNING", **_common_attributes_service_linking},
    {"message": "D", "level": "ERROR", **_common_attributes_service_linking},
    {"message": "E", "level": "CRITICAL", **_common_attributes_service_linking},
]


@reset_core_stats_engine()
def test_logging_outside_transaction(logger):
    @validate_log_events_outside_transaction(_test_logging_outside_transaction_events)
    @validate_log_event_count_outside_transaction(3)
    def test():
        exercise_logging(logger)

    test()


@reset_core_stats_engine()
def test_logging_newrelic_logs_not_forwarded(logger):
    @validate_log_event_count(0)
    @background_task()
    def test():
        nr_logger = logging.getLogger("newrelic")
        nr_logger.addHandler(logger.caplog)
        nr_logger.error("A")
        assert len(logger.caplog.records) == 1

    test()


_test_patcher_application_captured_event = {"message": "C-PATCH", "level": "WARNING"}
_test_patcher_application_captured_event.update(_common_attributes_trace_linking)


@reset_core_stats_engine()
def test_patcher_application_captured(logger):
    def patch(record):
        record["message"] += "-PATCH"
        return record

    @validate_log_events([_test_patcher_application_captured_event])
    @validate_log_event_count(1)
    @background_task()
    def test():
        set_trace_ids()
        patch_logger = logger.patch(patch)
        patch_logger.warning("C")

    test()


_test_logger_catch_event = {"level": "ERROR"}  # Message varies wildly, can't be included in test
_test_logger_catch_event.update(_common_attributes_trace_linking)


@reset_core_stats_engine()
def test_logger_catch(logger):
    @validate_log_events([_test_logger_catch_event])
    @validate_log_event_count(1)
    @background_task()
    def test():
        set_trace_ids()

        @logger.catch(reraise=True)
        def throw():
            raise ValueError("Test")

        try:
            with pytest.raises(ValueError):
                throw()
        except ValueError:
            pass

    test()
