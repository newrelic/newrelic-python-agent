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

from _test_agent import PROMPT, build_agent


def test_agent_no_harm(exercise_agent, set_trace_info):
    set_trace_info()
    agent = build_agent()
    events = exercise_agent(agent, PROMPT)

    assert len(events) == 1
    assert events[0].content.parts[0].text == "Paris"
