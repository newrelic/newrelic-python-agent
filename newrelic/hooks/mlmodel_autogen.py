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
import json
import sys
import traceback
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.common.package_version_utils import get_package_version
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

AUTOGEN_VERSION = (
    get_package_version("autogen-core")
    or get_package_version("autogen-agentchat")
    or get_package_version("autogen-ext")
)
RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Autogen instrumentation: Failed to record LLM events. Please report this issue to New Relic Support.\n%s"

_logger = logging.getLogger(__name__)


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


def wrap_on_messages_stream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    agent_name = getattr(instance, "name", "agent")
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"
    with FunctionTrace(name=function_trace_name, group="Llm", source=wrapped):
        return wrapped(*args, **kwargs)


def _get_llm_metadata(transaction):
    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}
    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def _extract_tool_output(return_val):
    try:
        data = json.loads(return_val[1].content)
        if data and isinstance(data, list) and "text" in data[0]:
            return data[0]["text"]
    except Exception:
        return None
    return None


def _construct_base_tool_event_dict(tool_id, run_id, tool_name, agent_name, linking_metadata, tool_input, transaction, settings):
    tool_event_dict = {
        "id": tool_id,
        "run_id": run_id,
        "name": tool_name,
        "span_id": linking_metadata.get("span.id"),
        "trace_id": linking_metadata.get("trace.id"),
        "agent_name": agent_name,
        "vendor": "autogen",
        "ingest_source": "Python",
    }
    if settings.ai_monitoring.record_content.enabled:
        tool_event_dict.update({"input": tool_input})
    tool_event_dict.update(_get_llm_metadata(transaction))

    return tool_event_dict


async def wrap__execute_tool_call(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Autogen", AUTOGEN_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_id = str(uuid.uuid4())
    bound_args = bind_args(wrapped, args, kwargs)
    linking_metadata = get_trace_linking_metadata()

    try:
        input = bound_args.get("tool_call").arguments
        tool_input = str(input) if input else None
        tool_name = bound_args.get("tool_call").name
        run_id = bound_args.get("tool_call").id
        agent_name = bound_args.get("agent_name")

        tool_event_dict = _construct_base_tool_event_dict(
            tool_id, run_id, tool_name, agent_name, linking_metadata, tool_input, transaction, settings
        )

        ft = FunctionTrace(name=wrapped.__name__, group="Llm/tool/Autogen")
        ft.__enter__()

        try:
            return_val = await wrapped(*args, **kwargs)
        except Exception:
            tool_event_dict.update({"duration": ft.duration * 1000, "error": True})
            transaction.record_custom_event("LlmTool", tool_event_dict)
            raise

        ft.__exit__(None, None, None)

        if not return_val:
            return return_val

        # If the tool was executed successfully, we can grab the tool output frmo the result
        tool_output = _extract_tool_output(return_val)

        if settings.ai_monitoring.record_content.enabled:
            tool_event_dict.update({"duration": ft.duration * 1000, "output": tool_output})

        transaction.record_custom_event("LlmTool", tool_event_dict)

    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

    return return_val


def instrument_autogen_agentchat_agents__assistant_agent(module):
    if hasattr(module, "AssistantAgent"):
        if hasattr(module.AssistantAgent, "on_messages_stream"):
            wrap_function_wrapper(module, "AssistantAgent.on_messages_stream", wrap_on_messages_stream)
        if hasattr(module.AssistantAgent, "_execute_tool_call"):
            wrap_function_wrapper(module, "AssistantAgent._execute_tool_call", wrap__execute_tool_call)


def instrument_autogen_ext_tools_mcp__base(module):
    if hasattr(module, "McpToolAdapter"):
        if hasattr(module.McpToolAdapter, "from_server_params"):
            wrap_function_wrapper(module, "McpToolAdapter.from_server_params", wrap_from_server_params)
