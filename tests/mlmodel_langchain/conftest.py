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
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixture.vcr import VCR_IGNORED_HEADERS, VCR_TIKTOKEN_ENCODINGS
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.ml_testing_utils import set_trace_info

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ai_monitoring.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_langchain)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_langchain)"],
)


VCR_IGNORED_HEADERS.extend(["host"])
VCR_TIKTOKEN_ENCODINGS.extend(["cl100k_base"])

EXPECTED_AGENT_RESPONSE = "Hello!"
EXPECTED_TOOL_OUTPUT = "Hello!"


@pytest.fixture
def openai_clients(vcr_recording):
    """
    This configures the OpenAI client to use a ReplayApiClient which
    will either record or replay responses depending on the mode.
    """
    from newrelic.core.config import _environ_as_bool

    if vcr_recording:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")
    else:
        openai_api_key = os.environ["OPENAI_API_KEY"] = "NOT-A-REAL-SECRET"

    chat = ChatOpenAI(api_key=openai_api_key, temperature=0.05, model="gpt-5.1")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    return chat, embeddings


@pytest.fixture
def embedding_openai_client(openai_clients):
    _, embedding_client = openai_clients
    return embedding_client


@pytest.fixture
def chat_openai_client(openai_clients):
    chat_client, _ = openai_clients
    return chat_client
