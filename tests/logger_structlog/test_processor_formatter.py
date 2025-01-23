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

"""
    This file tests structlog's ability to render structlog-based
    formatters within logging through structlog's `ProcessorFormatter` as
    a `logging.Formatter` for both logging as well as structlog log entries.
"""

# def test_basic():
#     import logging
#     import structlog

#     structlog.configure(
#         processors=[
#             # Prepare event dict for `ProcessorFormatter`.
#             structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
#         ],
#         logger_factory=structlog.stdlib.LoggerFactory(),
#     )

#     formatter = structlog.stdlib.ProcessorFormatter(
#         processors=[structlog.dev.ConsoleRenderer()],
#     )

#     handler = logging.StreamHandler()
#     # Use OUR `ProcessorFormatter` to format all `logging` entries.
#     handler.setFormatter(formatter)
#     logging_logger = logging.getLogger()
#     logging_logger.addHandler(handler)
#     logging_logger.setLevel(logging.WARNING)

#     structlog_logger = structlog.get_logger()

#     logging_logger.msg("Cat", a=42)
#     logging_logger.error("Dog")
#     logging_logger.critical("Elephant")

#     structlog_logger.info("Bird")
#     structlog_logger.error("Fish", events="water")
#     structlog_logger.critical("Giraffe")

#     assert len(structlog_caplog.caplog) == 6


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
        processors=[
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # logger_factory=structlog.stdlib.LoggerFactory(),
        logger_factory=lambda *args, **kwargs: structlog_caplog,
    )

    handler = CaplogHandler()
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.dev.ConsoleRenderer()],
    )

    handler.setFormatter(formatter)

    logging_logger = logging.getLogger()
    logging_logger.addHandler(handler)
    logging_logger.caplog = handler
    logging_logger.setLevel(logging.WARNING)

    structlog_logger = structlog.get_logger()

    yield logging_logger, structlog_logger
    # del handler.records[:]


@pytest.fixture
def exercise_both_logs(set_trace_ids, structlog_formatter_within_logging, structlog_caplog):
    def _exercise():
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


# Test local decorating
# ---------------------

# @pytest.fixture
# def exercise_logging_single_line(set_trace_ids, logger, structlog_caplog):
#     def _exercise():
#         set_trace_ids()
#         logger.error("A", key="value")
#         assert len(structlog_caplog.caplog) == 1

#     return _exercise


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
def test_local_log_decoration_inside_transaction(exercise_both_logs, structlog_caplog):
    @validate_log_event_count(5)
    @background_task()
    def test():
        exercise_both_logs()
        # assert get_metadata_string('A', True) in structlog_caplog.caplog[0]

    test()


@reset_core_stats_engine()
def test_local_log_decoration_outside_transaction(exercise_both_logs, structlog_caplog):
    @validate_log_event_count_outside_transaction(5)
    def test():
        exercise_both_logs()
        # assert get_metadata_string('A', False) in structlog_caplog.caplog[0]

    test()


# Test log forwarding
# ---------------------


# Test metrics
# ---------------------
