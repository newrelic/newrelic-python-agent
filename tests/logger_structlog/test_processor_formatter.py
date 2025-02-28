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
from testing_support.fixtures import override_application_settings, reset_core_stats_engine
from testing_support.validators.validate_custom_metrics_outside_transaction import (
    validate_custom_metrics_outside_transaction,
)
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.application import application_settings
from newrelic.api.background_task import background_task, current_transaction

"""
    This file tests structlog's ability to render structlog-based
    formatters within logging through structlog's `ProcessorFormatter` as
    a `logging.Formatter` for both logging as well as structlog log entries.
"""


@pytest.fixture(scope="function")
def structlog_formatter_within_logging(structlog_caplog):
    import logging

    import structlog

    class CaplogHandler(logging.StreamHandler):
        """
        To prevent possible issues with pytest's monkey patching
        use a custom Caplog handler to capture all records
        """

        def __init__(self, *args, **kwargs):
            self.records = []
            super(CaplogHandler, self).__init__(*args, **kwargs)

        def emit(self, record):
            self.records.append(self.format(record))

    structlog.configure(
        processors=[structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=lambda *args, **kwargs: structlog_caplog,
    )

    handler = CaplogHandler()
    formatter = structlog.stdlib.ProcessorFormatter(processors=[structlog.dev.ConsoleRenderer()])

    handler.setFormatter(formatter)

    logging_logger = logging.getLogger()
    logging_logger.addHandler(handler)
    logging_logger.caplog = handler
    logging_logger.setLevel(logging.WARNING)

    structlog_logger = structlog.get_logger(logger_attr=2)

    yield logging_logger, structlog_logger


@pytest.fixture
def exercise_both_loggers(set_trace_ids, structlog_formatter_within_logging, structlog_caplog):
    def _exercise():
        if current_transaction():
            set_trace_ids()

        logging_logger, structlog_logger = structlog_formatter_within_logging

        logging_logger.info("Cat", a=42)
        logging_logger.error("Dog")
        logging_logger.critical("Elephant")

        structlog_logger.info("Bird")
        structlog_logger.error("Fish", events="water")
        structlog_logger.critical("Giraffe")

        assert len(structlog_caplog.caplog) == 3  # set to INFO level
        assert len(logging_logger.caplog.records) == 2  # set to WARNING level

        assert "Dog" in logging_logger.caplog.records[0]
        assert "Elephant" in logging_logger.caplog.records[1]

        assert "Bird" in structlog_caplog.caplog[0]["event"]
        assert "Fish" in structlog_caplog.caplog[1]["event"]
        assert "Giraffe" in structlog_caplog.caplog[2]["event"]

    return _exercise


# Test attributes
# ---------------------


@validate_log_events(
    [
        {  # Fixed attributes
            "message": "context_attrs: arg1",
            "context.kwarg_attr": 1,
            "context.logger_attr": 2,
        }
    ]
)
@validate_log_event_count(1)
@background_task()
def test_processor_formatter_context_attributes(structlog_formatter_within_logging):
    _, structlog_logger = structlog_formatter_within_logging
    structlog_logger.error("context_attrs: %s", "arg1", kwarg_attr=1)


@validate_log_events([{"message": "A", "message.attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_processor_formatter_message_attributes(structlog_formatter_within_logging):
    _, structlog_logger = structlog_formatter_within_logging
    structlog_logger.error({"message": "A", "attr": 1})


# Test local decorating
# ---------------------


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
def test_processor_formatter_local_log_decoration_inside_transaction(exercise_both_loggers, structlog_caplog):
    @validate_log_event_count(5)
    @background_task()
    def test():
        exercise_both_loggers()
        assert get_metadata_string("Fish", True) in structlog_caplog.caplog[1]["event"]

    test()


@reset_core_stats_engine()
def test_processor_formatter_local_log_decoration_outside_transaction(exercise_both_loggers, structlog_caplog):
    @validate_log_event_count_outside_transaction(5)
    def test():
        exercise_both_loggers()
        assert get_metadata_string("Fish", False) in structlog_caplog.caplog[1]["event"]

    test()


# Test log forwarding
# ---------------------

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


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_processor_formatter_logging_inside_transaction(exercise_both_loggers):
    @validate_log_events(
        [
            {"message": "Dog", "level": "ERROR", **_common_attributes_trace_linking},
            {"message": "Elephant", "level": "CRITICAL", **_common_attributes_trace_linking},
            {"message": "Bird", "level": "INFO", **_common_attributes_trace_linking},
            {"message": "Fish", "level": "ERROR", **_common_attributes_trace_linking},
            {"message": "Giraffe", "level": "CRITICAL", **_common_attributes_trace_linking},
        ]
    )
    @validate_log_event_count(5)
    @background_task()
    def test():
        exercise_both_loggers()

    test()


@reset_core_stats_engine()
@override_application_settings({"application_logging.local_decorating.enabled": False})
def test_processor_formatter_logging_outside_transaction(exercise_both_loggers):
    @validate_log_events_outside_transaction(
        [
            {"message": "Dog", "level": "ERROR", **_common_attributes_service_linking},
            {"message": "Elephant", "level": "CRITICAL", **_common_attributes_service_linking},
            {"message": "Bird", "level": "INFO", **_common_attributes_service_linking},
            {"message": "Fish", "level": "ERROR", **_common_attributes_service_linking},
            {"message": "Giraffe", "level": "CRITICAL", **_common_attributes_service_linking},
        ]
    )
    @validate_log_event_count_outside_transaction(5)
    def test():
        exercise_both_loggers()

    test()


# Test metrics
# ---------------------

_test_logging_unscoped_metrics = [
    ("Logging/lines", 5),
    ("Logging/lines/INFO", 1),
    ("Logging/lines/ERROR", 2),
    ("Logging/lines/CRITICAL", 2),
]


@reset_core_stats_engine()
def test_processor_formatter_metrics_inside_transaction(exercise_both_loggers):
    @validate_transaction_metrics(
        "test_processor_formatter:test_processor_formatter_metrics_inside_transaction.<locals>.test",
        custom_metrics=_test_logging_unscoped_metrics,
        background_task=True,
    )
    @background_task()
    def test():
        exercise_both_loggers()

    test()


@reset_core_stats_engine()
def test_processor_formatter_metrics_outside_transaction(exercise_both_loggers):
    @validate_custom_metrics_outside_transaction(_test_logging_unscoped_metrics)
    def test():
        exercise_both_loggers()

    test()
