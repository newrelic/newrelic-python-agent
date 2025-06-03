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


async def wrap_call_tool(wrapped, instance, args, kwargs):
    tool_name = bind_call_tool(*args, **kwargs)
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{tool_name}"
    with FunctionTrace(name=function_trace_name, source=wrapped):
        return await wrapped(*args, **kwargs)


def bind_call_tool(name, *args, **kwargs):
    return name


def instrument_mcp_client_session(module):
    wrap_function_wrapper(module, "ClientSession.call_tool", wrap_call_tool)
