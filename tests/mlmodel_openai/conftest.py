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

import json
import os

import pytest
from _mock_external_openai_server import (
    MockExternalOpenAIServer,
    extract_shortened_prompt,
)
from testing_support.fixture.event_loop import (  # noqa: F401; pylint: disable=W0611
    event_loop as loop,
)
from testing_support.fixtures import (  # noqa: F401, pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

from newrelic.common.object_wrapper import wrap_function_wrapper

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ml_insights_event.enabled": True,
}
collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_openai)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_openai)"],
)

OPENAI_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "openai_audit.log")
OPENAI_AUDIT_LOG_CONTENTS = {}


@pytest.fixture(autouse=True, scope="session")
def openai_server():
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real OpenAI backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES=1 as
    an environment variable to run using the real OpenAI backend. (Default: mocking)
    """
    import openai

    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        # Use mocked OpenAI backend and prerecorded responses
        with MockExternalOpenAIServer() as server:
            openai.api_base = "http://localhost:%d" % server.port
            openai.api_key = "NOT-A-REAL-SECRET"
            yield
    else:
        # Use real OpenAI backend and record responses
        openai.api_key = os.environ.get("OPENAI_API_KEY", "")
        if not openai.api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")

        # Apply function wrappers to record data
        wrap_function_wrapper("openai.api_requestor", "APIRequestor.request", wrap_openai_api_requestor_request)
        yield  # Run tests

        # Write responses to audit log
        with open(OPENAI_AUDIT_LOG_FILE, "w") as audit_log_fp:
            json.dump(OPENAI_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)


# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = set(["x-request-id", "content-type"])


def wrap_openai_api_requestor_request(wrapped, instance, args, kwargs):
    params = bind_request_params(*args, **kwargs)
    if not params:
        return wrapped(*args, **kwargs)

    prompt = extract_shortened_prompt(params)

    # Send request
    result = wrapped(*args, **kwargs)

    # Clean up data
    data = result[0].data
    headers = result[0]._headers
    headers = dict(
        filter(
            lambda k: k[0].lower() in RECORDED_HEADERS
            or k[0].lower().startswith("openai")
            or k[0].lower().startswith("x-ratelimit"),
            headers.items(),
        )
    )

    # Log response
    OPENAI_AUDIT_LOG_CONTENTS[prompt] = headers, data  # Append response data to audit log
    return result


def bind_request_params(method, url, params=None, *args, **kwargs):
    return params
