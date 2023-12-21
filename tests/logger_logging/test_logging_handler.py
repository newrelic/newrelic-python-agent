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
from conftest import logger as conf_logger
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_function_called import validate_function_called
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import (
    validate_log_events_outside_transaction,
)

from newrelic.api.background_task import background_task
from newrelic.api.log import NewRelicLogForwardingHandler
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction

_common_attributes_service_linking = {
    "timestamp": None,
    "hostname": None,
    "entity.name": "Python Agent Test (logger_logging)",
    "entity.guid": None,
}
_common_attributes_trace_linking = {"span.id": "abcdefgh", "trace.id": "abcdefgh12345678"}


@pytest.fixture(scope="function")
def uninstrument_logging():
    instrumented = logging.Logger.callHandlers
    while hasattr(logging.Logger.callHandlers, "__wrapped__"):
        logging.Logger.callHandlers = logging.Logger.callHandlers.__wrapped__
    yield
    logging.Logger.callHandlers = instrumented


@pytest.fixture(scope="function")
def logger(conf_logger, uninstrument_logging):
    handler = NewRelicLogForwardingHandler()
    conf_logger.addHandler(handler)
    yield conf_logger
    conf_logger.removeHandler(handler)


def set_trace_ids():
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"


def exercise_logging(logger):
    set_trace_ids()
    logger.warning("C", extra={"key": "value"})
    assert len(logger.caplog.records) == 1


@override_application_settings(
    {
        "application_logging.forwarding.context_data.enabled": True,
    }
)
def test_handler_inside_transaction(logger):
    @validate_log_events(
        [
            {
                "message": "C",
                "level": "WARNING",
                "timestamp": None,
                "hostname": None,
                "entity.name": "Python Agent Test (logger_logging)",
                "entity.guid": None,
                "span.id": "abcdefgh",
                "trace.id": "abcdefgh12345678",
                "context.key": "value",
            }
        ]
    )
    @validate_log_event_count(1)
    @validate_function_called("newrelic.api.log", "NewRelicLogForwardingHandler.emit")
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
def test_handler_outside_transaction(logger):
    @validate_log_events_outside_transaction(
        [
            {
                "message": "C",
                "level": "WARNING",
                "timestamp": None,
                "hostname": None,
                "entity.name": "Python Agent Test (logger_logging)",
                "entity.guid": None,
                "context.key": "value",
            }
        ]
    )
    @validate_log_event_count_outside_transaction(1)
    @validate_function_called("newrelic.api.log", "NewRelicLogForwardingHandler.emit")
    def test():
        exercise_logging(logger)

    test()
