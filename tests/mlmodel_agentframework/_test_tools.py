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

from agent_framework import tool

from newrelic.api.transaction import current_transaction

from ._test_agent import AGENT_NAME

TOOL_NAME = "get_capital"


def get_capital(country: str) -> str:
    """Return the capital of a country."""
    capitals = {"France": "Paris", "Japan": "Tokyo"}
    return capitals.get(country, "Unknown")


@functools.wraps(get_capital)  # Make function names match
def _get_capital_with_transaction(country: str) -> str:
    assert current_transaction() is not None

    return get_capital(country)


@functools.wraps(get_capital)  # Make function names match
def _get_capital_without_transaction(country: str) -> str:
    assert current_transaction() is None

    return get_capital(country)


@functools.wraps(get_capital)  # Make function names match
def _get_capital_error(country: str) -> str:
    assert current_transaction() is not None

    raise ValueError("intentional tool failure")


get_capital_with_transaction = tool(func=_get_capital_with_transaction, name=TOOL_NAME)
get_capital_without_transaction = tool(func=_get_capital_without_transaction, name=TOOL_NAME)
get_capital_error = tool(func=_get_capital_error, name=TOOL_NAME)

EXPECTED_TOOL_INPUT_STR = "{'country': 'France'}"
EXPECTED_TOOL_OUTPUT_STR = "Paris"


def tool_recorded_event(record_content: bool):
    base = {
        "id": None,
        "run_id": None,
        "name": TOOL_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": AGENT_NAME,
        "vendor": "agentframework",
        "ingest_source": "Python",
        "duration": None,
    }
    if record_content:
        base["input"] = EXPECTED_TOOL_INPUT_STR
        base["output"] = EXPECTED_TOOL_OUTPUT_STR
    return [({"type": "LlmTool"}, base)]


def tool_recorded_event_error(record_content: bool):
    base = {
        "id": None,
        "run_id": None,
        "name": TOOL_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": AGENT_NAME,
        "vendor": "agentframework",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    }
    if record_content:
        base["input"] = EXPECTED_TOOL_INPUT_STR
    return [({"type": "LlmTool"}, base)]
