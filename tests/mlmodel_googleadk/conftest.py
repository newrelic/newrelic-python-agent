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

import functools
import os

import google.genai
import pytest
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)
from testing_support.ml_testing_utils import set_trace_info

from newrelic.common.package_version_utils import get_package_version

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
    app_name="Python Agent Test (mlmodel_googleadk)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_googleadk)"],
)


GOOGLEADK_VERSION = get_package_version("google-adk")
assert GOOGLEADK_VERSION, "Failed to pull google-adk version for supportability metric"


@pytest.fixture(autouse=True)
def patch_gemini_client(monkeypatch, vcr_recording):
    """
    Force accept-encoding: identity onto every google.genai.Client created during a test.

    The ADK Gemini model builds its own google.genai.Client internally (see
    google.adk.models.google_llm.Gemini.api_client), so HttpOptions can't be passed in via
    exercise_agent. Patching Client.__init__ disables gzip on the client the agent actually
    uses, keeping recorded VCR cassettes readable and diffable. Recording vs replay is
    controlled by passing --record-mode={all, none, new_episodes} to pytest.
    """

    # Ensure either fake or real credentials are supplied to the Client or it won't init
    if vcr_recording:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable required.")
    else:
        os.environ["GOOGLE_API_KEY"] = "FAKE_GEMINI_API_KEY"

    original_init = google.genai.Client.__init__

    @functools.wraps(original_init)
    def init_with_identity_encoding(self, *, http_options=None, **kwargs):
        # Disable gzip encoding to make the recorded responses easier to read and diff.
        if http_options is not None:
            # Make options into a mutable dict
            http_options = http_options.model_dump()
            # Patch existing headers to force accept-encoding: identity
            http_options["headers"] = {**(http_options.get("headers", {})), "accept-encoding": "identity"}
            # Reconstruct HttpOptions with the updated headers
            http_options = google.genai.types.HttpOptions(**http_options)
        else:
            http_options = google.genai.types.HttpOptions(headers={"accept-encoding": "identity"})

        return original_init(self, http_options=http_options, **kwargs)

    monkeypatch.setattr(google.genai.Client, "__init__", init_with_identity_encoding)


@pytest.fixture
def exercise_agent(loop):
    """Run an ADK Agent through a Runner, returning the collected list of Events."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    def _exercise_agent(agent, prompt, app_name="test_app", user_id="test_user"):
        session_service = InMemorySessionService()
        runner = Runner(app_name=app_name, agent=agent, session_service=session_service)

        async def _exercise():
            session = await session_service.create_session(app_name=app_name, user_id=user_id)
            new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            return [e async for e in runner.run_async(user_id=user_id, session_id=session.id, new_message=new_message)]

        return loop.run_until_complete(_exercise())

    return _exercise_agent
