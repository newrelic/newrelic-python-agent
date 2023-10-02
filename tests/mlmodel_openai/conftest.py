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

import os

import pytest
from testing_support.fixture.event_loop import (  # noqa: F401; pylint: disable=W0611
    event_loop as loop,
)
from testing_support.fixtures import (  # noqa: F401, pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.mock_external_openai_server import MockExternalOpenAIServer

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


@pytest.fixture(autouse=True)
def openai_server():
    import openai

    if os.environ.get("NEW_RELIC_TESTING_RECORD_OPENAI_RESPONSES", False):
        # Use real OpenAI backend and record responses
        openai.api_key = os.environ.get("OPENAI_API_KEY", "")
        if not openai.api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")

        yield
        return
    else:
        # Use mocked OpenAI backend and prerecorded responses
        with MockExternalOpenAIServer() as server:
            openai.api_base = "http://localhost:%d" % server.port
            openai.api_key = "NOT-A-REAL-SECRET"
            yield
