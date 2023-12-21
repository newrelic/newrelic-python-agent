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

from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import (
    validate_log_events_outside_transaction,
)

from newrelic.api.background_task import background_task

_event_attributes = {"message": "A", "context.key": "value"}


def exercise_logging(logger):
    logger.bind(key="value").error("A")
    assert len(logger.caplog.records) == 1


@override_application_settings(
    {
        "application_logging.forwarding.context_data.enabled": True,
    }
)
def test_attributes_inside_transaction(logger):
    @validate_log_events([_event_attributes])
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_logging(logger)

    test()


@reset_core_stats_engine()
@override_application_settings(
    {
        "application_logging.forwarding.context_data.enabled": True,
    }
)
def test_attributes_outside_transaction(logger):
    @validate_log_events_outside_transaction([_event_attributes])
    @validate_log_event_count_outside_transaction(1)
    def test():
        exercise_logging(logger)

    test()
