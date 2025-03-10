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

import platform

import pytest
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)

from newrelic.api.application import application_settings
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


def exercise_logging(logger, message="C"):
    set_trace_ids()

    logger.warning(message)


def get_metadata_string(log_message, is_txn):
    host = platform.uname()[1]
    assert host
    entity_guid = application_settings().entity_guid
    if is_txn:
        metadata_string = (
            f"NR-LINKING|{entity_guid}|{host}|abcdefgh12345678|abcdefgh|Python%20Agent%20Test%20%28logger_logging%29|"
        )
    else:
        metadata_string = f"NR-LINKING|{entity_guid}|{host}|||Python%20Agent%20Test%20%28logger_logging%29|"
    formatted_string = f"{log_message} {metadata_string}"
    return formatted_string


@reset_core_stats_engine()
def test_local_log_decoration_inside_transaction(instrumented_logger):
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_logging(instrumented_logger)
        assert instrumented_logger.caplog.records[0] == get_metadata_string("C", True)

    test()


@reset_core_stats_engine()
def test_local_log_decoration_outside_transaction(instrumented_logger):
    @validate_log_event_count_outside_transaction(1)
    def test():
        exercise_logging(instrumented_logger)
        assert instrumented_logger.caplog.records[0] == get_metadata_string("C", False)

    test()


@reset_core_stats_engine()
def test_local_log_decoration_dict_message(instrumented_logger):
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_logging(instrumented_logger, {"message": "dict_message"})
        assert instrumented_logger.caplog.records[0] == get_metadata_string("{'message': 'dict_message'}", True)

    test()
