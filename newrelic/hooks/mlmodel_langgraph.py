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

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args


def wrap_ToolNode__execute_tool_sync(wrapped, instance, args, kwargs):
    if not current_transaction():
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        agent_name = bound_args["request"].state["messages"][-1].name
        if agent_name:
            metadata = bound_args["config"]["metadata"]
            metadata["_nr_agent_name"] = agent_name
    except Exception:
        pass

    return wrapped(*args, **kwargs)


async def wrap_ToolNode__execute_tool_async(wrapped, instance, args, kwargs):
    if not current_transaction():
        return await wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        agent_name = bound_args["request"].state["messages"][-1].name
        if agent_name:
            metadata = bound_args["config"]["metadata"]
            metadata["_nr_agent_name"] = agent_name
    except Exception:
        pass

    return await wrapped(*args, **kwargs)


def instrument_langgraph_prebuilt_tool_node(module):
    if hasattr(module, "ToolNode"):
        if hasattr(module.ToolNode, "_execute_tool_sync"):
            wrap_function_wrapper(module, "ToolNode._execute_tool_sync", wrap_ToolNode__execute_tool_sync)
        if hasattr(module.ToolNode, "_execute_tool_async"):
            wrap_function_wrapper(module, "ToolNode._execute_tool_async", wrap_ToolNode__execute_tool_async)
