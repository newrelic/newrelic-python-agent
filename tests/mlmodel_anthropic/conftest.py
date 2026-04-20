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

import anthropic
import pytest
from _mock_external_anthropic_server import simple_get
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)
from testing_support.mock_external_http_server import MockExternalHTTPServer

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
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
    app_name="Python Agent Test (mlmodel_anthropic)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_anthropic)"],
)

ANTHROPIC_VERSION = get_package_version("anthropic")
ANTHROPIC_VERSION_METRIC = f"Supportability/Python/ML/Anthropic/{ANTHROPIC_VERSION}"

ANTHROPIC_AUDIT_LOG_FILE = Path(__file__).parent / "anthropic_audit.log"
ANTHROPIC_AUDIT_LOG_CONTENTS = {}
ANTHROPIC_STREAMING_AUDIT_LOG_CONTENTS = {}

DISALLOWED_HEADERS = {"content-length", "transfer-encoding", "server", "date"}


@pytest.fixture(scope="session")
def anthropic_clients():
    """
    Configures the Anthropic client to use a MockExternalHTTPServer which will serve
    pre-recorded responses. Set NEW_RELIC_TESTING_RECORD_ANTHROPIC_RESPONSES=1 to run
    against the real Anthropic backend and record new responses.
    """
    from newrelic.core.config import _environ_as_bool

    record_mode = _environ_as_bool("NEW_RELIC_TESTING_RECORD_ANTHROPIC_RESPONSES", False)

    if record_mode:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        base_url = os.environ.get("ANTHROPIC_BASE_URL")  # Optional, only for non-public Anthropic backends
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variables required. For non-public Anthropic backends, also specify ANTHROPIC_BASE_URL."
            )

        wrap_function_wrapper("httpx._client", "Client.send", wrap_httpx_client_send)

        sync_client = anthropic.Anthropic(base_url=base_url, api_key=api_key)
        async_client = anthropic.AsyncAnthropic(base_url=base_url, api_key=api_key)
        yield sync_client, async_client

        # Write responses to audit log
        with ANTHROPIC_AUDIT_LOG_FILE.open("w") as audit_log_fp:
            audit_log_fp.write("RESPONSES = ")
            json.dump(ANTHROPIC_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
            audit_log_fp.write("\nSTREAMED_RESPONSES = ")
            json.dump(ANTHROPIC_STREAMING_AUDIT_LOG_CONTENTS, fp=audit_log_fp, indent=4)
    else:
        with MockExternalHTTPServer(handler=simple_get) as server:
            sync_client = anthropic.Anthropic(base_url=f"http://localhost:{server.port}", api_key="ANTHROPIC_API_KEY")
            async_client = anthropic.AsyncAnthropic(
                base_url=f"http://localhost:{server.port}", api_key="ANTHROPIC_API_KEY"
            )
            yield sync_client, async_client


@pytest.fixture(scope="session")
def sync_anthropic_client(anthropic_clients):
    sync_client, _ = anthropic_clients
    return sync_client


@pytest.fixture(scope="session")
def async_anthropic_client(anthropic_clients):
    _, async_client = anthropic_clients
    return async_client


def wrap_httpx_client_send(wrapped, instance, args, kwargs):
    response = wrapped(*args, **kwargs)

    # Extract request data to dump to audit log file
    bound_args = bind_args(wrapped, args, kwargs)
    streaming = bound_args.get("stream", False)
    request = bound_args["request"]
    request_body = json.loads(request.content.decode("utf-8"))
    prompt = request_body["messages"][0]["content"]
    headers = dict(filter(lambda item: item[0].lower() not in DISALLOWED_HEADERS, response.headers.items()))

    # Append response data to audit log
    if not streaming:
        ANTHROPIC_AUDIT_LOG_CONTENTS[prompt] = [headers, response.status_code, response.json()]
    else:
        # Read and replace the stream with a generator
        response_chunks = list(response.stream)
        response.stream._stream = (chunk for chunk in response_chunks)

        # Log the resulting stream chunks
        decoded_chunks = [chunk.decode("utf-8") for chunk in response_chunks]
        ANTHROPIC_STREAMING_AUDIT_LOG_CONTENTS[prompt] = [headers, response.status_code, decoded_chunks]

    return response


@pytest.fixture(scope="session", params=["sync", "async"])
def is_async(request):
    return request.param == "async"


@pytest.fixture(scope="session", params=["create"])  # TODO: Re-enable streaming once instrumented.
# @pytest.fixture(scope="session", params=["create", "create_stream", "stream", "text_stream"])
def interaction_method(request):
    return request.param


@pytest.fixture(scope="session")
def is_streaming(interaction_method):
    return interaction_method != "create"


@pytest.fixture(scope="session")
def exercise_model(loop, sync_anthropic_client, async_anthropic_client, is_async, interaction_method):
    def exercise_model_sync(*args, **kwargs):
        if interaction_method == "create":
            return sync_anthropic_client.messages.create(*args, **kwargs)
        elif interaction_method == "create_stream":
            stream = sync_anthropic_client.messages.create(*args, stream=True, **kwargs)
            return list(stream)
        elif interaction_method == "stream":
            with sync_anthropic_client.messages.stream(*args, **kwargs) as stream:
                return list(stream)
        elif interaction_method == "text_stream":
            with sync_anthropic_client.messages.stream(*args, **kwargs) as stream:
                return list(stream.text_stream)
        else:
            raise NotImplementedError

    def exercise_model_async(*args, **kwargs):
        async def _exercise_model_async():
            if interaction_method == "create":
                return await async_anthropic_client.messages.create(*args, **kwargs)
            elif interaction_method == "create_stream":
                stream = await async_anthropic_client.messages.create(*args, stream=True, **kwargs)
                return [chunk async for chunk in stream]
            elif interaction_method == "stream":
                async with async_anthropic_client.messages.stream(*args, **kwargs) as stream:
                    return [event async for event in stream]
            elif interaction_method == "text_stream":
                async with async_anthropic_client.messages.stream(*args, **kwargs) as stream:
                    return [event async for event in stream.text_stream]
            else:
                raise NotImplementedError

        return loop.run_until_complete(_exercise_model_async())

    return exercise_model_sync if not is_async else exercise_model_async
