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

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name
from newrelic.common.signature import bind_args


def wrap_run_stream(wrapped, instance, args, kwargs):
    with FunctionTrace(name="run_stream_test", source=wrapped):
        return wrapped(*args, **kwargs)


async def wrap_from_server_params(wrapped, instance, args, kwargs):
    func_name = callable_name(wrapped)
    bound_args = bind_args(wrapped, args, kwargs)
    tool_name = bound_args.get("tool_name") or "tool"
    function_trace_name = f"{func_name}/{tool_name}"
    with FunctionTrace(name=function_trace_name, source=wrapped):
        return await wrapped(*args, **kwargs)


def wrap_on_messages_stream(wrapped, instance, args, kwargs):
    agent_name = getattr(instance, "name", "agent") 
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"
    with FunctionTrace(name=function_trace_name, source=wrapped):
        return wrapped(*args, **kwargs)


def instrument_autogen_agentchat_teams__group_chat__base_group_chat(module):
    wrap_function_wrapper(module, "BaseGroupChat.run_stream", wrap_run_stream)


def instrument_autogen_agentchat_agents__assistant_agent(module):
    if hasattr(module, "AssistantAgent"):
        if hasattr(module.AssistantAgent, "on_messages_stream"):
            wrap_function_wrapper(module, "AssistantAgent.on_messages_stream", wrap_on_messages_stream)


def instrument_autogen_ext_tools_mcp__base(module):
    if hasattr(module, "McpToolAdapter"):
        if hasattr(module.McpToolAdapter, "from_server_params"):
            wrap_function_wrapper(module, "McpToolAdapter.from_server_params", wrap_from_server_params)
