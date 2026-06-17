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
from pathlib import Path

import google.genai
import pytest
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)

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

GEMINI_VERSION = google.genai.__version__
GEMINI_VERSION_METRIC = f"Supportability/Python/ML/Gemini/{GEMINI_VERSION}"


@pytest.fixture
def gemini_client(vcr_recording, is_vertex):
    """
    This configures the Gemini client to use a ReplayApiClient which will either record or replay responses depending
    on the mode. The mode can be controlled by setting NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES=1 as an environment
    variable to run using the real Gemini backend. (Default: mocking)
    """

    if vcr_recording:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable required.")
    else:
        google_api_key = os.environ["GOOGLE_API_KEY"] = "FAKE_GEMINI_API_KEY"

    gemini_client = google.genai.Client(api_key=google_api_key, vertexai=is_vertex)

    yield gemini_client

    gemini_client.close()


@pytest.fixture(scope="session", params=["standard", "vertex"])
def is_vertex(request):
    return request.param == "vertex"


@pytest.fixture(scope="session", params=["invoke", "stream"])
def is_streaming(request):
    return request.param == "stream"


@pytest.fixture(scope="session", params=["sync", "async"])
def is_async(request):
    return request.param == "async"


@pytest.fixture(scope="session", params=["chat", "model"])
def is_chat(request):
    return request.param == "chat"


@pytest.fixture
def exercise_text_model(loop, gemini_client, is_async, is_chat, is_streaming):
    # Pick the sync or async client before we make the chat object for convenience
    client = gemini_client.aio if is_async else gemini_client

    def _exercise_text_model(*args, **kwargs):
        if is_chat:
            chat = client.chats.create(model=kwargs.pop("model"))
            kwargs["message"] = kwargs.pop("contents")  # Make the kwargs compatible

            if not is_streaming:
                if not is_async:
                    return chat.send_message(*args, **kwargs)
                else:
                    return loop.run_until_complete(chat.send_message(*args, **kwargs))
            else:
                if not is_async:
                    return list(chat.send_message_stream(*args, **kwargs))
                else:

                    async def _exercise_agen():
                        return [event async for event in await chat.send_message_stream(*args, **kwargs)]

                    return loop.run_until_complete(_exercise_agen())
        else:
            if not is_streaming:
                if not is_async:
                    return client.models.generate_content(*args, **kwargs)
                else:
                    return loop.run_until_complete(client.models.generate_content(*args, **kwargs))
            else:
                if not is_async:
                    return list(client.models.generate_content_stream(*args, **kwargs))
                else:

                    async def _exercise_agen():
                        return [event async for event in await client.models.generate_content_stream(*args, **kwargs)]

                    return loop.run_until_complete(_exercise_agen())

    return _exercise_text_model


@pytest.fixture
def exercise_embedding_model(loop, gemini_client, is_async):
    # Pick the sync or async client for convenience
    client = gemini_client.aio if is_async else gemini_client

    def _exercise_embedding_model(*args, **kwargs):
        if not is_async:
            return client.models.embed_content(*args, **kwargs)
        else:
            return loop.run_until_complete(client.models.embed_content(*args, **kwargs))

    return _exercise_embedding_model
