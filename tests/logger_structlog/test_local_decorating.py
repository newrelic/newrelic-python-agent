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

from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)

from newrelic.api.application import application_settings
from newrelic.api.background_task import background_task


def get_metadata_string(log_message, is_txn):
    host = platform.uname()[1]
    assert host
    entity_guid = application_settings().entity_guid
    if is_txn:
        metadata_string = (
            f"NR-LINKING|{entity_guid}|{host}|abcdefgh12345678|abcdefgh|Python%20Agent%20Test%20%28logger_structlog%29|"
        )
    else:
        metadata_string = f"NR-LINKING|{entity_guid}|{host}|||Python%20Agent%20Test%20%28logger_structlog%29|"
    formatted_string = f"{log_message} {metadata_string}"
    return formatted_string


@reset_core_stats_engine()
def test_local_log_decoration_inside_transaction(exercise_logging_single_line, structlog_caplog):
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_logging_single_line()
        assert get_metadata_string("A", True) in structlog_caplog.caplog[0]

    test()


@reset_core_stats_engine()
def test_local_log_decoration_outside_transaction(exercise_logging_single_line, structlog_caplog):
    @validate_log_event_count_outside_transaction(1)
    def test():
        exercise_logging_single_line()
        assert get_metadata_string("A", False) in structlog_caplog.caplog[0]

    test()
