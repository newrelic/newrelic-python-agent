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

import pytest
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "application_logging.enabled": True,
    "application_logging.forwarding.enabled": True,
    "application_logging.metrics.enabled": True,
    "application_logging.local_decorating.enabled": True,
    "application_logging.forwarding.context_data.enabled": True,
    "event_harvest_config.harvest_limits.log_event_data": 100000,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (logger_structlog)", default_settings=_default_settings
)


@pytest.fixture(scope="session")
def StructLogCapLog():
    from structlog import PrintLogger

    class _StructLogCapLog(PrintLogger):
        def __init__(self, caplog=None):
            self.caplog = caplog if caplog is not None else []

        def msg(self, event, **kwargs):
            self.caplog.append(event)
            return

        log = debug = info = warn = warning = msg
        fatal = failure = err = error = critical = exception = msg

        def __repr__(self):
            return f"<StructLogCapLog {str(id(self))}>"

        __str__ = __repr__

    return _StructLogCapLog


@pytest.fixture
def set_trace_ids():
    def _set():
        txn = current_transaction()
        if txn:
            txn._trace_id = "abcdefgh12345678"
        trace = current_trace()
        if trace:
            trace.guid = "abcdefgh"

    return _set


def drop_event_processor(logger, method_name, event_dict):
    from structlog import DropEvent

    if method_name == "info":
        raise DropEvent
    else:
        return event_dict


@pytest.fixture(scope="function")
def structlog_caplog(StructLogCapLog):
    return StructLogCapLog()


@pytest.fixture(scope="function")
def logger(structlog_caplog):
    import structlog

    structlog.configure(processors=[], logger_factory=lambda *args, **kwargs: structlog_caplog)
    _logger = structlog.get_logger()
    return _logger


@pytest.fixture(scope="function")
def filtering_logger(structlog_caplog):
    import structlog

    structlog.configure(processors=[drop_event_processor], logger_factory=lambda *args, **kwargs: structlog_caplog)
    _filtering_logger = structlog.get_logger()
    return _filtering_logger


@pytest.fixture
def exercise_logging_multiple_lines(set_trace_ids, logger, structlog_caplog):
    def _exercise():
        set_trace_ids()

        logger.msg("Cat", a=42)
        logger.error("Dog")
        logger.critical("Elephant")

        assert len(structlog_caplog.caplog) == 3

        assert "Cat" in structlog_caplog.caplog[0]
        assert "Dog" in structlog_caplog.caplog[1]
        assert "Elephant" in structlog_caplog.caplog[2]

    return _exercise


@pytest.fixture
def exercise_filtering_logging_multiple_lines(set_trace_ids, filtering_logger, structlog_caplog):
    def _exercise():
        set_trace_ids()

        filtering_logger.msg("Cat", a=42)
        filtering_logger.error("Dog")
        filtering_logger.critical("Elephant")

        assert len(structlog_caplog.caplog) == 2

        assert "Cat" not in structlog_caplog.caplog[0]
        assert "Dog" in structlog_caplog.caplog[0]
        assert "Elephant" in structlog_caplog.caplog[1]

    return _exercise


@pytest.fixture
def exercise_logging_single_line(set_trace_ids, logger, structlog_caplog):
    def _exercise():
        set_trace_ids()
        logger.error("A", key="value")
        assert len(structlog_caplog.caplog) == 1

    return _exercise
