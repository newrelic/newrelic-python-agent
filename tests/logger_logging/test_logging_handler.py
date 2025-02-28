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
from conftest import instrumented_logger as conf_logger  # noqa, pylint: disable=W0611
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_function_called import validate_function_called
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction

from newrelic.api.background_task import background_task
from newrelic.api.log import NewRelicLogForwardingHandler
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction


@pytest.fixture(scope="function")
def uninstrument_logging():
    instrumented = logging.Logger.callHandlers
    while hasattr(logging.Logger.callHandlers, "__wrapped__"):
        logging.Logger.callHandlers = logging.Logger.callHandlers.__wrapped__  # noqa, pylint: disable=E1101
    yield
    logging.Logger.callHandlers = instrumented


@pytest.fixture(scope="function")
def formatting_logger(conf_logger, uninstrument_logging):
    handler = NewRelicLogForwardingHandler()
    handler.setFormatter(logging.Formatter(r"%(levelname)s - %(message)s"))
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


class DictMessageFormatter(logging.Formatter):
    def format(self, record):
        message = record.msg
        if isinstance(message, dict):
            message["formatter_attr"] = 1
        return message


def test_handler_with_formatter(formatting_logger):
    @validate_log_events(
        [
            {
                "message": "WARNING - C",
                "level": "WARNING",
                "timestamp": None,
                "hostname": None,
                "entity.name": "Python Agent Test (logger_logging)",
                "entity.guid": None,
                "span.id": "abcdefgh",
                "trace.id": "abcdefgh12345678",
                "context.key": "value",  # Extra attr
                "context.module": "test_logging_handler",  # Default attr
            }
        ]
    )
    @validate_log_event_count(1)
    @validate_function_called("newrelic.api.log", "NewRelicLogForwardingHandler.emit")
    @background_task()
    def test():
        set_trace_ids()
        formatting_logger.warning("C", extra={"key": "value"})
        assert len(formatting_logger.caplog.records) == 1

    test()


def test_handler_dict_message_no_formatter(formatting_logger):
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
                "message.attr": 3,  # Message attr
            }
        ]
    )
    @validate_log_event_count(1)
    @validate_function_called("newrelic.api.log", "NewRelicLogForwardingHandler.emit")
    @background_task()
    def test():
        set_trace_ids()
        formatting_logger.handlers[1].setFormatter(None)  # Turn formatter off to enable dict message support
        formatting_logger.warning({"message": "C", "attr": 3})
        assert len(formatting_logger.caplog.records) == 1

    test()


def test_handler_dict_message_with_formatter(formatting_logger):
    @validate_log_events(
        [
            {
                "message": None,  # Python 2 makes order of dict attributes random, assert for this is below
                "level": "WARNING",
                "timestamp": None,
                "hostname": None,
                "entity.name": "Python Agent Test (logger_logging)",
                "entity.guid": None,
                "span.id": "abcdefgh",
                "trace.id": "abcdefgh12345678",
            }
        ],
        forgone_attrs=["message.attr"],  # Explicit formatters take precedence over dict message support
    )
    @validate_log_event_count(1)
    @validate_function_called("newrelic.api.log", "NewRelicLogForwardingHandler.emit")
    @background_task()
    def test():
        set_trace_ids()
        formatting_logger.warning({"message": "C", "attr": 3})
        assert len(formatting_logger.caplog.records) == 1

        # Python 2 makes order of dict attributes random. Message will not be consistent.
        # Grab the event directly off the transaction to compare message manually
        captured_events = list(current_transaction()._log_events)
        assert len(captured_events) == 1

        # Accept anything that looks like the correct types.
        assert captured_events[0].message.startswith("WARNING - {")

    test()


def test_handler_formatter_returns_dict_message(formatting_logger):
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
                "message.attr": 3,  # Message attr
                "message.formatter_attr": 1,  # Formatter message attr
            }
        ]
    )
    @validate_log_event_count(1)
    @validate_function_called("newrelic.api.log", "NewRelicLogForwardingHandler.emit")
    @background_task()
    def test():
        set_trace_ids()
        formatting_logger.handlers[1].setFormatter(DictMessageFormatter())  # Set formatter to return a dict
        formatting_logger.warning({"message": "C", "attr": 3})
        assert len(formatting_logger.caplog.records) == 1

    test()
