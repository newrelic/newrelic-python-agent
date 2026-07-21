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

import openai
import pytest
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
)

from newrelic.common.package_version_utils import get_package_version_tuple

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
    app_name="Python Agent Test (mlmodel_openai)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_openai)"],
)

OPENAI_VERSION = get_package_version_tuple("openai")


if OPENAI_VERSION < (1, 0):
    collect_ignore = [
        "test_chat_completion.py",
        "test_chat_completion_error.py",
        "test_embeddings.py",
        "test_embeddings_error.py",
        "test_chat_completion_stream.py",
        "test_chat_completion_stream_error.py",
        "test_embeddings_stream.py",
        # The Responses API only exists in openai v1+.
        "test_responses.py",
        "test_responses_error.py",
        "test_responses_stream.py",
        "test_responses_stream_error.py",
    ]
else:
    collect_ignore = [
        "test_embeddings_v0.py",
        "test_embeddings_error_v0.py",
        "test_chat_completion_v0.py",
        "test_chat_completion_error_v0.py",
        "test_chat_completion_stream_v0.py",
        "test_chat_completion_stream_error_v0.py",
    ]


@pytest.fixture(autouse=True)
def openai_api_key(vcr_recording):
    """Real key from the environment when recording, a fake key when replaying through VCR."""
    if vcr_recording:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")
    else:
        openai_api_key = os.environ.setdefault("OPENAI_API_KEY", "NOT-A-REAL-SECRET")

    # For v0 clients, set the API key on the module level
    if OPENAI_VERSION < (1, 0):
        openai.api_key = openai_api_key


@pytest.fixture
def sync_openai_client(openai_api_key):
    return openai.OpenAI(api_key=openai_api_key)


@pytest.fixture
def async_openai_client(openai_api_key):
    return openai.AsyncOpenAI(api_key=openai_api_key)
