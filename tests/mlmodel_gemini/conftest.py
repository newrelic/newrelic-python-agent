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
from pathlib import Path

import google.genai
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

GEMINI_VERSION = google.genai.__version__
GEMINI_VERSION_METRIC = f"Supportability/Python/ML/Gemini/{GEMINI_VERSION}"


GEMINI_AUDIT_LOG_FILE = Path(__file__).parent / "gemini_audit.log"
GEMINI_AUDIT_LOG_CONTENTS = {}
# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = {"content-type"}


@pytest.fixture
def replay_id(is_vertex, is_streaming, is_chat):
    pytest_name = os.environ.get("PYTEST_CURRENT_TEST").split("::")
    test_module = Path(pytest_name[0]).with_suffix("").name
    test_name = pytest_name[-1].split(" ")[0].split("[")[0]
    # Don't use the actual parameter values in the replay ID to avoid having different replays for certain parameters like is_async.
    test_params_name = f"{'streaming' if is_streaming else 'invoke'}-{'chat' if is_chat else 'model'}-{'vertex' if is_vertex else 'standard'}"

    return f"{test_module}/{test_name}/{test_params_name}"


@pytest.fixture
def gemini_clients(replay_id):
    """
    This configures the Gemini client to use a ReplayApiClient which will either record or replay responses depending
    on the mode. The mode can be controlled by setting NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES=1 as an environment
    variable to run using the real Gemini backend. (Default: mocking)
    """
    from newrelic.core.config import _environ_as_bool

    record_mode = _environ_as_bool("NEW_RELIC_TESTING_RECORD_GEMINI_RESPONSES", False)
    replay_client_mode = "record" if record_mode else "replay"

    if record_mode:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable required.")
    else:
        google_api_key = os.environ["GOOGLE_API_KEY"] = "GEMINI_API_KEY"

    # Set the replay directory to a location in this test suite.
    os.environ["GOOGLE_GENAI_REPLAYS_DIRECTORY"] = str(Path(__file__).parent / "replays")

    # Monkeypatch the Gemini client to use the replay client which will either record or replay responses depending on the mode.
    replay_client = google.genai._replay_api_client.ReplayApiClient(mode=replay_client_mode, replay_id=replay_id)
    google.genai.client.Client._get_api_client = lambda self, *args, **kwargs: replay_client
    gemini_dev_client = google.genai.Client(api_key=google_api_key)

    yield gemini_dev_client

    gemini_dev_client._api_client.close()
    gemini_dev_client.close()


@pytest.fixture
def gemini_dev_client(gemini_clients):
    # Once VertexAI is enabled, gemini_clients() will yield two different clients up that will be unpacked here
    gemini_dev_client = gemini_clients
    return gemini_dev_client


@pytest.fixture(scope="session")
def wrap_httpx_client_send(extract_shortened_prompt):
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


# @pytest.fixture(scope="session", params=["vertex", "standard"])
@pytest.fixture(scope="session", params=["standard"])
def is_vertex(request):
    return request.param == "vertex"

# @pytest.fixture(scope="session", params=["invoke", "stream"])
@pytest.fixture(scope="session", params=["invoke"])  # TODO Put this back
def is_streaming(request):
    return request.param == "stream"


@pytest.fixture(scope="session", params=["sync", "async"])
def is_async(request):
    return request.param == "async"


@pytest.fixture(scope="session", params=["chat", "model"])
def is_chat(request):
    return request.param == "chat"


@pytest.fixture
def exercise_text_model(loop, gemini_dev_client, is_async, is_chat, is_streaming):
    # Pick the sync or async client before we make the chat object for convenience
    client = gemini_dev_client.aio if is_async else gemini_dev_client

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
                        return [event async for event in chat.send_message_stream(*args, **kwargs)]

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
                        return [event async for event in client.models.generate_content_stream(*args, **kwargs)]

                    return loop.run_until_complete(_exercise_agen())

    return _exercise_text_model


@pytest.fixture
def exercise_embedding_model(loop, gemini_dev_client, is_async):
    # Pick the sync or async client for convenience
    client = gemini_dev_client.aio if is_async else gemini_dev_client

    def _exercise_embedding_model(*args, **kwargs):
        if not is_async:
            return client.models.embed_content(*args, **kwargs)
        else:
            return loop.run_until_complete(client.models.embed_content(*args, **kwargs))

    return _exercise_embedding_model
