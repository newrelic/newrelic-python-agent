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


def test_unset_llm_token_count_callback():
    settings = application().settings
    set_llm_token_count_callback(lambda model, content: 45)
    assert callable(settings.ai_monitoring.llm_token_count_callback)
    set_llm_token_count_callback(None)

    assert settings.ai_monitoring.llm_token_count_callback is None


@pytest.mark.parametrize(
    "set_args,call_args,expected_value",
    [
        ((lambda model, content: 45,), ("model", "content"), 45),
        ((lambda model, content: 45, application().settings), ("model", "content"), 45),
        ((lambda model, content: 1.1,), ("model", "content"), None),
        ((lambda model, content: -1,), ("model", "content"), None),
        ((lambda model, content: 45,), (None, "content"), None),
        ((lambda model, content: 45,), ("model", None), None),
    ],
)
def test_set_llm_token_count_callback(set_args, call_args, expected_value):
    settings = application().settings
    set_llm_token_count_callback(*set_args)
    assert settings.ai_monitoring.llm_token_count_callback(*call_args) == expected_value



def test_exception_in_user_callback():
    settings = application().settings

    def user_exc():
        raise TypeError()
    
    set_llm_token_count_callback(user_exc)

    with pytest.raises(TypeError):
        assert settings.ai_monitoring.llm_token_count_callback("model", "content")


def test_with_application_not_active():
    settings = application(activate=False).settings

    set_llm_token_count_callback(lambda model, content: 45)
    assert settings.ai_monitoring.llm_token_count_callback("model", "content") == 45

