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
from structlog import DropEvent, PrintLogger

from testing_support.fixtures import (
    code_coverage_fixture,
    collector_agent_registration_fixture,
    collector_available_fixture,
)

_coverage_source = [
    "newrelic.hooks.logger_structlog",
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "application_logging.enabled": True,
    "application_logging.forwarding.enabled": True,
    "application_logging.metrics.enabled": True,
    "application_logging.local_decorating.enabled": True,
    "event_harvest_config.harvest_limits.log_event_data": 100000,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (logger_structlog)",
    default_settings=_default_settings,
)


class StructLogCapLog(PrintLogger):
    def __init__(self, caplog):
        self.caplog = caplog if caplog is not None else []

    def msg(self, event, **kwargs):
        self.caplog.append(event)
        return

    log = debug = info = warn = warning = msg
    fatal = failure = err = error = critical = exception = msg

    def __repr__(self):
        return "<StructLogCapLog %s>" % str(id(self))

    __str__ = __repr__

def drop_event_processor(logger, method_name, event_dict):
    if method_name == "info":
        raise DropEvent
    else:
        return event_dict

@pytest.fixture(scope="function")
def structlog_caplog():
    yield list()


@pytest.fixture(scope="function")
def logger(structlog_caplog):
    import structlog
    structlog.configure(processors=[], logger_factory=lambda *args, **kwargs: StructLogCapLog(structlog_caplog))
    _logger = structlog.get_logger()
    yield _logger

@pytest.fixture(scope="function")
def filtering_logger(structlog_caplog):
    import structlog
    structlog.configure(processors=[drop_event_processor], logger_factory=lambda *args, **kwargs: StructLogCapLog(structlog_caplog))
    _filtering_logger = structlog.get_logger()
    yield _filtering_logger
