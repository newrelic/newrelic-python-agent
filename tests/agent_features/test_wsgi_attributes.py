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

import webtest
from testing_support.fixtures import (
    dt_enabled,
    override_application_settings,
    validate_error_event_attributes,
    validate_transaction_error_trace_attributes,
    validate_transaction_event_attributes,
)
from testing_support.sample_applications import fully_featured_app

WSGI_ATTRIBUTES = [
    "wsgi.input.seconds",
    "wsgi.input.bytes",
    "wsgi.input.calls.read",
    "wsgi.input.calls.readline",
    "wsgi.input.calls.readlines",
    "wsgi.output.seconds",
    "wsgi.output.bytes",
    "wsgi.output.calls.write",
    "wsgi.output.calls.yield",
]
required_attributes = {"agent": WSGI_ATTRIBUTES, "intrinsic": {}, "user": {}}

app = webtest.TestApp(fully_featured_app)


@validate_transaction_event_attributes(required_attributes)
@validate_error_event_attributes(required_attributes)
@validate_transaction_error_trace_attributes(required_attributes)
@override_application_settings({"attributes.include": ["*"]})
@dt_enabled
def test_wsgi_attributes():
    app.post_json(
        "/", {"foo": "bar"}, extra_environ={"n_errors": "1", "err_message": "oops"}
    )
