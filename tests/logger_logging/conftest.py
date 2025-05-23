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
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

from newrelic.api.log import NewRelicLogForwardingHandler

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "application_logging.enabled": True,
    "application_logging.forwarding.enabled": True,
    "application_logging.forwarding.context_data.enabled": True,
    "application_logging.metrics.enabled": True,
    "application_logging.local_decorating.enabled": True,
    "event_harvest_config.harvest_limits.log_event_data": 100000,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (logger_logging)", default_settings=_default_settings
)


class CaplogHandler(logging.StreamHandler):
    """
    To prevent possible issues with pytest's monkey patching
    use a custom Caplog handler to capture all records
    """

    def __init__(self, *args, **kwargs):
        self.records = []
        super().__init__(*args, **kwargs)

    def emit(self, record):
        self.records.append(self.format(record))


@pytest.fixture(params=["instrumented_logger", "forwarding_handler"])
def logger(request):
    _logger = logging.getLogger("my_app")
    caplog = CaplogHandler()
    _logger.addHandler(caplog)
    _logger.caplog = caplog
    _logger.setLevel(logging.WARNING)

    # Save instrumentation so we can disable it
    instrumented = logging.Logger.callHandlers

    forwarding_handler = None
    if request.param == "forwarding_handler":
        forwarding_handler = NewRelicLogForwardingHandler()
        _logger.addHandler(forwarding_handler)

        # Uninstrument Logging
        logging.Logger.callHandlers = logging.Logger.callHandlers.__wrapped__

    yield _logger
    del caplog.records[:]

    _logger.removeHandler(caplog)
    if forwarding_handler:
        _logger.removeHandler(forwarding_handler)

    # Reinstrument logging in case it was uninstrumented
    logging.Logger.callHandlers = instrumented


@pytest.fixture
def instrumented_logger():
    _logger = logging.getLogger("my_app")
    caplog = CaplogHandler()
    _logger.addHandler(caplog)
    _logger.caplog = caplog
    _logger.setLevel(logging.WARNING)

    yield _logger
    del caplog.records[:]

    _logger.removeHandler(caplog)
