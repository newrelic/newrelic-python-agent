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

from conftest import AGENT_NAME
from crewai.tools import tool

TOOL_NAME = "get_capital"


def _get_capital(country: str) -> str:
    """Return a country's capital."""
    capitals = {"France": "Paris", "Japan": "Tokyo"}
    return capitals.get(country, "Unknown")


@functools.wraps(_get_capital)  # Make tool name and description match
def _raising_capital(country: str) -> str:
    raise ValueError("intentional tool failure")


get_capital = tool(TOOL_NAME)(_get_capital)
raising_capital = tool(TOOL_NAME)(_raising_capital)

EXPECTED_TOOL_INPUT_STR = "{'country': 'France'}"
EXPECTED_TOOL_OUTPUT_STR = "Paris"


def tool_recorded_event(record_content: bool, output: str = EXPECTED_TOOL_OUTPUT_STR):
    base = {
        "id": None,
        "name": TOOL_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": AGENT_NAME,
        "vendor": "crewai",
        "ingest_source": "Python",
        "duration": None,
    }
    if record_content:
        base["input"] = EXPECTED_TOOL_INPUT_STR
        base["output"] = output
    return [({"type": "LlmTool"}, base)]


def tool_recorded_event_error(record_content: bool):
    base = {
        "id": None,
        "name": TOOL_NAME,
        "span_id": None,
        "trace_id": "trace-id",
        "agent_name": AGENT_NAME,
        "vendor": "crewai",
        "ingest_source": "Python",
        "duration": None,
        "error": True,
    }
    if record_content:
        base["input"] = EXPECTED_TOOL_INPUT_STR
    return [({"type": "LlmTool"}, base)]
