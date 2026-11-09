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

from conftest import AGENT_NAME

MANAGER_NAME = "Crew Manager"


_BASE = {"id": None, "span_id": None, "trace_id": "trace-id", "vendor": "crewai", "ingest_source": "Python"}


def agent_event(name=AGENT_NAME, error=False):
    """One LlmAgent event for an Agent-level span."""
    event = dict(_BASE, name=name, duration=None)
    if error:
        event["error"] = True
    return ({"type": "LlmAgent"}, event)


def agent_recorded_events(num_agents=1, error=False):
    names = [AGENT_NAME] if num_agents == 1 else [f"{AGENT_NAME}_{i}" for i in range(num_agents)]
    return [agent_event(name=n, error=error) for n in names]
