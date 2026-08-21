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

# CrewAI phones home for telemetry and prompts interactively to enable execution tracing.
# Disable both (and mark a test environment) before crewai is imported so tests run offline
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["CREWAI_DISABLE_TRACKING"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TESTING"] = "true"

import pytest
from crewai import Agent, Crew, Task
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixture.vcr import *  # noqa: F403
from testing_support.fixture.vcr import VCR_IGNORED_HEADERS
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
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
    app_name="Python Agent Test (mlmodel_crewai)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_crewai)"],
)

AGENT_NAME = "my_agent"
AGENT_GOAL = "Answer in one word."
AGENT_BACKSTORY = "A concise assistant."
PROMPT = "What is the capital of France?"
TOOL_PROMPT = "Use get_capital on France. Answer with only the city name."

VCR_IGNORED_HEADERS.extend(["x-stainless-read-timeout"])

CREWAI_VERSION = get_package_version("crewai")
assert CREWAI_VERSION, "Failed to pull crewai version for supportability metric"

EXPECTED_CREWAI_VERSION_METRIC = (f"Supportability/Python/ML/CrewAI/{CREWAI_VERSION}", 1)
EXPECTED_VERSION_METRICS = [EXPECTED_CREWAI_VERSION_METRIC]

MODEL = "gpt-4o-mini"


def _openai_api_key(vcr_recording):
    if vcr_recording:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required.")
        return api_key
    os.environ["OPENAI_API_KEY"] = "NOT-A-REAL-SECRET"
    return "NOT-A-REAL-SECRET"


def _build_llm(vcr_recording):
    from crewai import LLM

    return LLM(model=MODEL, api_key=_openai_api_key(vcr_recording), temperature=0.0, seed=42)


@pytest.fixture
def crewai_native_llm(vcr_recording):
    """
    Return a CrewAI LLM that drives the agent through native (function-calling) tool calls.

    This is the default for OpenAI/Anthropic/Gemini/Azure/Bedrock models, and routes tool
    execution through CrewAgentExecutor._handle_native_tool_calls, bypassing ToolUsage entirely.
    """
    return _build_llm(vcr_recording)


@pytest.fixture
def crewai_llm(vcr_recording, monkeypatch):
    """
    Return a CrewAI LLM that drives the agent through the ReAct (text) path instead.

    CrewAgentExecutor._invoke_loop picks the native path whenever llm.supports_function_calling()
    is true, so reaching ToolUsage._use/_ause -- the methods the agent instruments -- requires
    forcing that off.
    """
    llm = _build_llm(vcr_recording)
    monkeypatch.setattr(type(llm), "supports_function_calling", lambda self: False)
    return llm


@pytest.fixture
def build_agent():
    def _build_agent(llm, tools=None, max_retry_limit=None, max_iter=None):
        """
        Return an Agent driven by the given LLM. tools defaults to none (pure-LLM path).
        """
        kwargs = {}
        if max_retry_limit is not None:
            kwargs["max_retry_limit"] = max_retry_limit
        if max_iter is not None:
            kwargs["max_iter"] = max_iter
        return Agent(role=AGENT_NAME, goal=AGENT_GOAL, backstory=AGENT_BACKSTORY, llm=llm, tools=tools or [], **kwargs)

    return _build_agent


@pytest.fixture
def build_crew(build_agent):
    def _build_crew(
        llm, tools=None, description=PROMPT, expected_output="One word.", max_retry_limit=None, max_iter=None
    ):
        """Return a single-agent Crew. A Crew routes work through Agent.execute_task and ToolUsage."""
        agent = build_agent(llm, tools=tools, max_retry_limit=max_retry_limit, max_iter=max_iter)
        task = Task(description=description, expected_output=expected_output, agent=agent)
        return Crew(agents=[agent], tasks=[task])

    return _build_crew
