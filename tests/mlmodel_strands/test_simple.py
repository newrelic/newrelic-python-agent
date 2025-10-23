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

from strands import Agent, tool

from newrelic.api.background_task import background_task


# Example tool for testing purposes
@tool
def add_exclamation(message: str) -> str:
    return f"{message}!"


# TODO: Remove this file once all real tests are in place


@background_task()
def test_simple_run_agent(set_trace_info, single_tool_model):
    set_trace_info()
    my_agent = Agent(name="my_agent", model=single_tool_model, tools=[add_exclamation])

    response = my_agent("Run the tools.")
    assert response.message["content"][0]["text"] == "Success!"
    assert response.metrics.tool_metrics["add_exclamation"].success_count == 1
