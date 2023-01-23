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

import json
import platform

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


def exercise_logging(logger):
    set_trace_ids()

    logger.warning("C")


def exercise_logging_json(logger):
    set_trace_ids()

    logger.warning('{"first_name": "Hugh", "last_name": "Man"}')


@reset_core_stats_engine()
def test_local_log_decoration_inside_transaction(logger):
    @validate_log_event_count(1)
    @background_task()
    def test():
        host = platform.uname()[1]
        assert host
        entity_guid = application_settings().entity_guid
        entity_name = "Python%20Agent%20Test%20%28logger_logging%29"
        exercise_logging(logger)
        assert logger.caplog.records[0] == "C NR-LINKING|%s|%s|abcdefgh12345678|abcdefgh|%s|" % (
            entity_guid,
            host,
            entity_name,
        )

    test()


@reset_core_stats_engine()
def test_local_log_decoration_inside_transaction_with_json(logger):
    @validate_log_event_count(1)
    @background_task()
    def test():
        host = platform.uname()[1]
        assert host
        entity_guid = application_settings().entity_guid
        entity_name = "Python%20Agent%20Test%20%28logger_logging%29"
        exercise_logging_json(logger)
        sorted_json = json.dumps(json.loads(logger.caplog.records[0]), sort_keys=True)
        assert (
            sorted_json
            == '{"NR-LINKING": "%s|%s|abcdefgh12345678|abcdefgh|%s|", "first_name": "Hugh", "last_name": "Man"}'
            % (
                entity_guid,
                host,
                entity_name,
            )
        )

    test()


@reset_core_stats_engine()
def test_local_log_decoration_outside_transaction(logger):
    @validate_log_event_count_outside_transaction(1)
    def test():
        host = platform.uname()[1]
        assert host
        entity_guid = application_settings().entity_guid
        entity_name = "Python%20Agent%20Test%20%28logger_logging%29"
        exercise_logging(logger)
        assert logger.caplog.records[0] == "C NR-LINKING|%s|%s|||%s|" % (entity_guid, host, entity_name)

    test()


@reset_core_stats_engine()
def test_local_log_decoration_outside_transaction_with_json(logger):
    @validate_log_event_count_outside_transaction(1)
    def test():
        host = platform.uname()[1]
        assert host
        entity_guid = application_settings().entity_guid
        entity_name = "Python%20Agent%20Test%20%28logger_logging%29"
        exercise_logging_json(logger)
        sorted_json = json.dumps(json.loads(logger.caplog.records[0]), sort_keys=True)
        assert sorted_json == '{"NR-LINKING": "%s|%s|||%s|", "first_name": "Hugh", "last_name": "Man"}' % (
            entity_guid,
            host,
            entity_name,
        )

    test()
