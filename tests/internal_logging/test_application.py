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
import sys
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import _log_records
from testing_support.validators.validate_log_events import validate_log_events

@pytest.fixture()
def logger():
    _logger = logging.getLogger("my_app")
    _logger.addHandler(logging.StreamHandler(stream=sys.stdout))
    return _logger

@background_task()
def test_no_harm(caplog, logger):
    with caplog.at_level(logging.INFO):
        logger.info("hi")

    assert len(caplog.records) == 1
    assert caplog.messages == ["hi"]
    caplog.clear()

    record, message = _log_records.pop()
    assert "hi" in message


@validate_log_events(1)
@background_task()
def test_send_to_collector(logger):
    logger.critical("Bonjour")
