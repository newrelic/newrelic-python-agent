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

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args


async def wrap_from_server_params(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    func_name = callable_name(wrapped)
    bound_args = bind_args(wrapped, args, kwargs)
    tool_name = bound_args.get("tool_name") or "tool"
    function_trace_name = f"{func_name}/{tool_name}"
    with FunctionTrace(name=function_trace_name, group="Llm", source=wrapped):
        return await wrapped(*args, **kwargs)


def instrument_autogen_ext_tools_mcp__base(module):
    if hasattr(module, "McpToolAdapter"):
        if hasattr(module.McpToolAdapter, "from_server_params"):
            wrap_function_wrapper(module, "McpToolAdapter.from_server_params", wrap_from_server_params)
