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

from conftest import CaplogHandler

from newrelic.api.background_task import background_task
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.fixtures import override_application_settings



@pytest.fixture(scope="function")
def filepath_logger():
    import loguru
    _logger = loguru.logger
    caplog = CaplogHandler()
    handler_id = _logger.add(caplog, level="WARNING", format="{file}:{function} - {message}")
    _logger.caplog = caplog
    yield _logger
    del caplog.records[:]
    _logger.remove(handler_id)


@override_application_settings({
    "application_logging.local_decorating.enabled": False,
})
@reset_core_stats_engine()
def test_filepath_inspection(filepath_logger):
    # Test for regression in stack inspection that caused log messages.
    # See https://github.com/newrelic/newrelic-python-agent/issues/603

    @validate_log_events([{"message": "A", "level": "ERROR"}])
    @validate_log_event_count(1)
    @background_task()
    def test():
        filepath_logger.error("A")
        assert len(filepath_logger.caplog.records) == 1
        record = filepath_logger.caplog.records[0]
        assert record == "test_stack_inspection.py:test - A", record

    test()
