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

import json
import logging
import sys
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.llm_utils import _get_llm_metadata
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

CREWAI_VERSION = get_package_version("crewai")

RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in CrewAI instrumentation: Failed to record LLM events. Please report this issue to New Relic Support.\n%s"
TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE = "Exception occurred in CrewAI instrumentation: Failed to extract tool information. If the issue persists, report this issue to New Relic Support.\n"

_logger = logging.getLogger(__name__)


def _get_tool_name(tool, calling):
    # The tool name lives on both the resolved tool and the calling object;
    # prefer the tool itself and fall back to the calling object.
    return getattr(tool, "name", None) or getattr(calling, "tool_name", None) or "tool"


def _construct_base_tool_event_dict(instance, tool, calling, tool_id, transaction, settings, linking_metadata):
    try:
        _input = getattr(calling, "arguments", None)
        tool_input = str(_input) if _input else None
        tool_name = _get_tool_name(tool, calling)
        agent_name = getattr(getattr(instance, "agent", None), "role", "agent")

        tool_event_dict = {
            "id": tool_id,
            "name": tool_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "agent_name": agent_name,
            "vendor": "crewai",
            "ingest_source": "Python",
        }
        if settings.ai_monitoring.record_content.enabled:
            tool_event_dict["input"] = tool_input
        tool_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        tool_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return tool_event_dict


def _start_tool_trace(wrapped, instance, tool, calling, transaction):
    transaction.add_ml_model_info("CrewAI", CREWAI_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_name = _get_tool_name(tool, calling)
    func_name = callable_name(wrapped)
    agentic_subcomponent_data = {"type": "APM-AI_TOOL", "name": tool_name}

    ft = FunctionTrace(name=f"{func_name}/{tool_name}", group="Llm/tool/CrewAI")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))
    return ft


def wrap_tool_usage__use(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        tool = bound_args.get("tool")
        calling = bound_args.get("calling")
    except Exception:
        tool = calling = None
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)

    tool_id = str(uuid.uuid4())
    ft = _start_tool_trace(wrapped, instance, tool, calling, transaction)
    linking_metadata = get_trace_linking_metadata()
    tool_event_dict = _construct_base_tool_event_dict(
        instance, tool, calling, tool_id, transaction, settings, linking_metadata
    )

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"tool_id": tool_id})
        ft.__exit__(*sys.exc_info())
        tool_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmTool", tool_event_dict)
        raise

    ft.__exit__(None, None, None)
    _record_tool_success(transaction, settings, tool_event_dict, ft, return_val)
    return return_val


async def wrap_tool_usage__ause(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        tool = bound_args.get("tool")
        calling = bound_args.get("calling")
    except Exception:
        tool = calling = None
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)

    tool_id = str(uuid.uuid4())
    ft = _start_tool_trace(wrapped, instance, tool, calling, transaction)
    linking_metadata = get_trace_linking_metadata()
    tool_event_dict = _construct_base_tool_event_dict(
        instance, tool, calling, tool_id, transaction, settings, linking_metadata
    )

    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"tool_id": tool_id})
        ft.__exit__(*sys.exc_info())
        tool_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmTool", tool_event_dict)
        raise

    ft.__exit__(None, None, None)
    _record_tool_success(transaction, settings, tool_event_dict, ft, return_val)
    return return_val


def _record_tool_success(transaction, settings, tool_event_dict, ft, return_val):
    try:
        tool_event_dict.update({"duration": ft.duration * 1000})
        # _use/_ause return the formatted result string (tool output)
        if settings.ai_monitoring.record_content.enabled:
            tool_event_dict["output"] = str(return_val) if return_val else None
        transaction.record_custom_event("LlmTool", tool_event_dict)
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)


def instrument_crewai_tools_tool_usage(module):
    if hasattr(module, "ToolUsage"):
        if hasattr(module.ToolUsage, "_use"):
            wrap_function_wrapper(module, "ToolUsage._use", wrap_tool_usage__use)
        if hasattr(module.ToolUsage, "_ause"):
            wrap_function_wrapper(module, "ToolUsage._ause", wrap_tool_usage__ause)


def wrap_tool_usage_event_init(wrapped, instance, args, kwargs):
    # Runs synchronously, in-line with whichever code constructed the event (e.g.
    # CrewAgentExecutor._handle_native_tool_calls), so it's a safe place to capture the
    # already-parsed tool name/args/output/error that crewai packages onto these events,
    wrapped(*args, **kwargs)

    transaction = current_transaction()
    if not transaction:
        return

    captured_events = getattr(transaction, "_nr_crewai_native_tool_events", None)
    if captured_events is None:
        return

    if type(instance).__name__ in ("ToolUsageFinishedEvent", "ToolUsageErrorEvent"):
        captured_events.append(instance)


def _construct_native_tool_event_dict(event, tool_id, transaction, settings, linking_metadata):
    try:
        tool_name = (getattr(event, "tool_name", None) if event else None) or "tool"
        tool_input = getattr(event, "tool_args", None) if event else None
        tool_input = str(tool_input) if tool_input else None
        agent_name = (getattr(event, "agent_role", None) if event else None) or "agent"

        tool_event_dict = {
            "id": tool_id,
            "name": tool_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "agent_name": agent_name,
            "vendor": "crewai",
            "ingest_source": "Python",
        }
        if settings.ai_monitoring.record_content.enabled:
            tool_event_dict["input"] = tool_input
        tool_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        tool_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return tool_event_dict


def wrap_crew_agent_executor__handle_native_tool_calls(wrapped, instance, args, kwargs):
    # Covers the native function-calling tool path, which is the default for OpenAI/Anthropic/
    # Gemini/Azure/Bedrock models in current crewai versions and bypasses ToolUsage entirely
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("CrewAI", CREWAI_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_id = str(uuid.uuid4())
    func_name = callable_name(wrapped)
    linking_metadata = get_trace_linking_metadata()

    ft = FunctionTrace(name=func_name, group="Llm/tool/CrewAI")
    ft.__enter__()

    # Save/restore rather than blindly clearing, in case of reentrant native tool calls
    # within the same transaction (e.g. an agent delegating to another agent).
    previous_events = getattr(transaction, "_nr_crewai_native_tool_events", None)
    transaction._nr_crewai_native_tool_events = []
    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"tool_id": tool_id})
        ft.__exit__(*sys.exc_info())
        if previous_events is None:
            del transaction._nr_crewai_native_tool_events
        else:
            transaction._nr_crewai_native_tool_events = previous_events
        raise

    captured_events = transaction._nr_crewai_native_tool_events
    if previous_events is None:
        del transaction._nr_crewai_native_tool_events
    else:
        transaction._nr_crewai_native_tool_events = previous_events

    # _handle_native_tool_calls emits ToolUsageErrorEvent AND (unconditionally) ToolUsageFinishedEvent
    # on a tool failure, so prefer the error event when both are present.
    error_event = next((e for e in captured_events if type(e).__name__ == "ToolUsageErrorEvent"), None)
    finished_event = error_event or next(
        (e for e in captured_events if type(e).__name__ == "ToolUsageFinishedEvent"), None
    )

    tool_name = (getattr(finished_event, "tool_name", None) if finished_event is not None else None) or "tool"
    ft.name = f"{func_name}/{tool_name}"
    agentic_subcomponent_data = {"type": "APM-AI_TOOL", "name": tool_name}
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))
    ft.__exit__(None, None, None)

    tool_event_dict = _construct_native_tool_event_dict(
        finished_event, tool_id, transaction, settings, linking_metadata
    )
    tool_event_dict["duration"] = ft.duration * 1000
    if error_event is not None:
        # crewai catches native tool-call errors internally and never raises them, so there is
        # no transaction error to notice here -- only this event's error flag signals failure.
        tool_event_dict["error"] = True
    elif settings.ai_monitoring.record_content.enabled and finished_event is not None:
        output = getattr(finished_event, "output", None)
        tool_event_dict["output"] = str(output) if output is not None else None

    transaction.record_custom_event("LlmTool", tool_event_dict)
    return return_val


def instrument_crewai_events_types_tool_usage_events(module):
    if hasattr(module, "ToolUsageEvent"):
        wrap_function_wrapper(module, "ToolUsageEvent.__init__", wrap_tool_usage_event_init)


def instrument_crewai_agents_crew_agent_executor(module):
    if hasattr(module, "CrewAgentExecutor") and hasattr(module.CrewAgentExecutor, "_handle_native_tool_calls"):
        wrap_function_wrapper(
            module, "CrewAgentExecutor._handle_native_tool_calls", wrap_crew_agent_executor__handle_native_tool_calls
        )
