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

from _mock_external_gemini_server import (
    MockExternalGeminiServer,
    extract_shortened_prompt,
    simple_get,
)

import pytest
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.signature import bind_args

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
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


@pytest.fixture(scope="session")
def gemini_clients(MockExternalGeminiServer):  # noqa: F811
    """
    This configures the Gemini client and returns it
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES", True):
        with MockExternalGeminiServer() as server:
            gemini_dev_client = google.genai.Client(api_key='GEMINI_API_KEY', http_options=google.genai.types.HttpOptions(base_url=f"http://localhost:{server.port}"))
            yield gemini_dev_client
    # else:
    #     openai_api_key = os.environ.get("OPENAI_API_KEY")
    #     if not openai_api_key:
    #         raise RuntimeError("OPENAI_API_KEY environment variable required.")
    #     chat = ChatOpenAI(api_key=openai_api_key)
    #     embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    #     yield chat, embeddings


@pytest.fixture(scope="session")
def gemini_dev_client(gemini_clients):
    gemini_dev_client = gemini_clients
    return gemini_dev_client


@pytest.fixture(scope="session")
def vertexai_client(gemini_clients):
    _, vertexai_client = gemini_clients
    return vertexai_client


@pytest.fixture(autouse=True, scope="session")
def gemini_server(
    gemini_clients,
):
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real OpenAI backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES=1 as
    an environment variable to run using the real OpenAI backend. (Default: mocking)
    """
    from newrelic.core.config import _environ_as_bool

    if _environ_as_bool("NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES", False):
        wrap_function_wrapper("httpx._client", "Client.send", wrap_httpx_client_send)
        wrap_function_wrapper("openai._streaming", "Stream._iter_events", wrap_stream_iter_events)
        yield  # Run tests
        # Write responses to audit log
        with open(OPENAI_AUDIT_LOG_FILE, "w") as audit_log_fp:
            json.dump(OPENAI_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
    else:
        # We are mocking responses so we don't need to do anything in this case.
        yield
