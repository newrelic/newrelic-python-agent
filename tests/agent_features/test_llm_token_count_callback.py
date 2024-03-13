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

import sys
import threading
import traceback

import pytest
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_error_event_attributes import (
    validate_error_event_attributes,
)
from testing_support.validators.validate_error_event_attributes_outside_transaction import (
    validate_error_event_attributes_outside_transaction,
)
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_error_trace_attributes_outside_transaction import (
    validate_error_trace_attributes_outside_transaction,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.ml_model import set_llm_token_count_callback
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import web_transaction
from newrelic.common.object_names import callable_name


def basic_callback(model, content):
    return 45


def test_clear_llm_token_count_callback():
    settings = application().settings
    set_llm_token_count_callback(basic_callback)
    assert settings.ai_monitoring.llm_token_count_callback is not None, "Failed to set callback."
    set_llm_token_count_callback(None)
    assert settings.ai_monitoring.llm_token_count_callback is None, "Failed to clear callback."


@pytest.mark.parametrize(
    "callback,accepted", [(basic_callback, True), (lambda x, y: None, True), (None, False), ("string", False)]
)
def test_set_llm_token_count_callback(callback, accepted):
    try:
        set_llm_token_count_callback(callback)
        settings = application().settings
        if accepted:
            assert settings.ai_monitoring.llm_token_count_callback is not None, "Failed to set callback."
        else:
            assert settings.ai_monitoring.llm_token_count_callback is None, "Accepted bad callback."
    finally:
        set_llm_token_count_callback(None)
