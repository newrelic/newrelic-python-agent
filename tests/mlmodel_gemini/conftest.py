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
import google.genai

from _mock_external_gemini_server import MockExternalGeminiServer, extract_shortened_prompt, simple_get

import pytest
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow-downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ml_insights_events.enabled": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_gemini)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_gemini)"],
)


GEMINI_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "gemini_audit.log")
GEMINI_AUDIT_LOG_CONTENTS = {}
# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = set(["content-type"])


@pytest.fixture(scope="session")
def gemini_clients(MockExternalGeminiServer):  # noqa: F811
    """
    This configures the Gemini client and returns it
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES", True):
        with MockExternalGeminiServer() as server:
            gemini_dev_client = google.genai.Client(
                api_key="GEMINI_API_KEY",
                http_options=google.genai.types.HttpOptions(base_url=f"http://localhost:{server.port}"),
            )
            yield gemini_dev_client
    else:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable required.")

        gemini_dev_client = google.genai.Client(api_key=google_api_key)
        yield gemini_dev_client


@pytest.fixture(scope="session")
def gemini_dev_client(gemini_clients):
    # Once VertexAI is enabled, gemini_clients() will yield two different clients up that will be unpacked here
    gemini_dev_client = gemini_clients
    return gemini_dev_client


# @pytest.fixture(scope="session")
# def vertexai_client(gemini_clients):
#     # This will eventually also be yielded up in gemini_clients() to test again the Vertex AI API
#     _, vertexai_client = gemini_clients
#     return vertexai_client


@pytest.fixture(autouse=True, scope="session")
def gemini_server(gemini_clients, wrap_httpx_client_send):
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real Gemini backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES=1 as
    an environment variable to run using the real Gemini backend. (Default: mocking)
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES", True):
        wrap_function_wrapper("httpx._client", "Client.send", wrap_httpx_client_send)
        yield  # Run tests
        # Write responses to audit log
        with open(GEMINI_AUDIT_LOG_FILE, "w") as audit_log_fp:
            json.dump(GEMINI_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
    else:
        # We are mocking responses so we don't need to do anything in this case.
        yield


@pytest.fixture(scope="session")
def wrap_httpx_client_send(extract_shortened_prompt):  # noqa: F811
    def _wrap_httpx_client_send(wrapped, instance, args, kwargs):
        bound_args = bind_args(wrapped, args, kwargs)
        request = bound_args["request"]
        if not request:
            return wrapped(*args, **kwargs)

        params = json.loads(request.content.decode("utf-8"))
        prompt = extract_shortened_prompt(params)

        # Send request
        response = wrapped(*args, **kwargs)

        if response.status_code >= 500 or response.status_code < 200:
            prompt = "error"

        rheaders = response.headers
        headers = dict(
            filter(lambda k: k[0].lower() in RECORDED_HEADERS or k[0].lower().startswith("x-goog"), rheaders.items())
        )
        body = json.loads(response.content.decode("utf-8"))
        GEMINI_AUDIT_LOG_CONTENTS[prompt] = headers, response.status_code, body  # Append response data to log
        return response

    return _wrap_httpx_client_send
