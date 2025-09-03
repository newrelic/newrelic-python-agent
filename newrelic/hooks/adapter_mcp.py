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

import logging

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args

_logger = logging.getLogger(__name__)


async def wrap_call_tool(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    func_name = callable_name(wrapped)
    bound_args = bind_args(wrapped, args, kwargs)
    tool_name = bound_args.get("name") or "tool"
    function_trace_name = f"{func_name}/{tool_name}"

    with FunctionTrace(name=function_trace_name, group="Llm/tool/MCP", source=wrapped):
        return await wrapped(*args, **kwargs)


async def wrap_read_resource(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    func_name = callable_name(wrapped)
    bound_args = bind_args(wrapped, args, kwargs)
    # Set a default value in case we can't parse out the URI scheme successfully
    resource_scheme = "resource"

    try:
        resource_uri = bound_args.get("uri")
        resource_scheme = getattr(resource_uri, "scheme", "resource")
    except Exception:
        _logger.warning("Unable to parse resource URI scheme for MCP read_resource call")

    function_trace_name = f"{func_name}/{resource_scheme}"

    with FunctionTrace(name=function_trace_name, group="Llm/resource/MCP", source=wrapped):
        return await wrapped(*args, **kwargs)


async def wrap_get_prompt(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    func_name = callable_name(wrapped)
    bound_args = bind_args(wrapped, args, kwargs)
    prompt_name = bound_args.get("name") or "prompt"
    function_trace_name = f"{func_name}/{prompt_name}"

    with FunctionTrace(name=function_trace_name, group="Llm/prompt/MCP", source=wrapped):
        return await wrapped(*args, **kwargs)


def instrument_mcp_client_session(module):
    if hasattr(module, "ClientSession"):
        if hasattr(module.ClientSession, "call_tool"):
            wrap_function_wrapper(module, "ClientSession.call_tool", wrap_call_tool)
        if hasattr(module.ClientSession, "read_resource"):
            wrap_function_wrapper(module, "ClientSession.read_resource", wrap_read_resource)
        if hasattr(module.ClientSession, "get_prompt"):
            wrap_function_wrapper(module, "ClientSession.get_prompt", wrap_get_prompt)
