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
import webtest
from testing_support.fixtures import override_application_settings
from testing_support.sample_applications import (
    simple_app,
    simple_custom_event_app,
    simple_exceptional_app,
)
from testing_support.validators.validate_custom_event_collector_json import (
    validate_custom_event_collector_json,
)
from testing_support.validators.validate_error_event_collector_json import (
    validate_error_event_collector_json,
)
from testing_support.validators.validate_error_trace_collector_json import (
    validate_error_trace_collector_json,
)
from testing_support.validators.validate_log_event_collector_json import (
    validate_log_event_collector_json,
)
from testing_support.validators.validate_transaction_event_collector_json import (
    validate_transaction_event_collector_json,
)
from testing_support.validators.validate_tt_collector_json import (
    validate_tt_collector_json,
)

exceptional_application = webtest.TestApp(simple_exceptional_app)
normal_application = webtest.TestApp(simple_app)
custom_event_application = webtest.TestApp(simple_custom_event_app)


@validate_error_trace_collector_json()
def test_error_trace_json():
    try:
        exceptional_application.get("/")
    except ValueError:
        pass


@validate_error_event_collector_json()
def test_error_event_json():
    try:
        exceptional_application.get("/")
    except ValueError:
        pass


@validate_tt_collector_json()
def test_transaction_trace_json():
    normal_application.get("/")


@validate_tt_collector_json(exclude_request_uri=True)
@override_application_settings({"attributes.exclude": set(("request.uri",))})
def test_transaction_trace_json_no_request_uri():
    normal_application.get("/")


@validate_transaction_event_collector_json()
def test_transaction_event_json():
    normal_application.get("/")


@validate_custom_event_collector_json()
def test_custom_event_json():
    custom_event_application.get("/")


@pytest.mark.xfail(reason="Unwritten validator")
@validate_log_event_collector_json
def test_log_event_json():
    normal_application.get("/")
    raise NotImplementedError("Fix my validator")
