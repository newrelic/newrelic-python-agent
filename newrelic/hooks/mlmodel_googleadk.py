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

_logger = logging.getLogger(__name__)
GOOGLEADK_VERSION = get_package_version("google-adk")

RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Google ADK instrumentation: Failed to record LLM events. Please report this issue to New Relic Support."
TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE = "Exception occurred in Google ADK instrumentation: Failed to extract tool information. If the issue persists, report this issue to New Relic support.\n"


async def wrap__execute_single_function_call_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    transaction.add_ml_model_info("GoogleADK", GOOGLEADK_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_name = "tool"
    run_id = ""
    tool_input = None
    agent_name = "agent"
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        function_call = bound_args.get("function_call")
        agent = bound_args.get("agent")
        if function_call is not None:
            tool_name = getattr(function_call, "name", "tool") or "tool"
            run_id = getattr(function_call, "id", "") or ""
            tool_input = getattr(function_call, "args", None)
        if agent is not None:
            agent_name = getattr(agent, "name", "agent") or "agent"
    except Exception:
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)

    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{tool_name}"
    agentic_subcomponent_data = {"type": "APM-AI_TOOL", "name": tool_name}

    ft = FunctionTrace(name=function_trace_name, group="Llm/tool/GoogleADK")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))
    linking_metadata = get_trace_linking_metadata()
    tool_id = str(uuid.uuid4())

    try:
        tool_output = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"tool_id": tool_id})
        ft.__exit__(*sys.exc_info())
        try:
            tool_event_dict = _construct_base_tool_event_dict(
                tool_name=tool_name,
                tool_id=tool_id,
                run_id=run_id,
                tool_input=tool_input,
                tool_output=None,
                agent_name=agent_name,
                error=True,
                transaction=transaction,
                linking_metadata=linking_metadata,
            )
            if tool_event_dict:
                tool_event_dict["duration"] = ft.duration * 1000
                transaction.record_custom_event("LlmTool", tool_event_dict)
        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        raise

    ft.__exit__(None, None, None)
    try:
        response_dict = _extract_tool_response_dict(tool_output)
        tool_event_dict = _construct_base_tool_event_dict(
            tool_name=tool_name,
            tool_id=tool_id,
            run_id=run_id,
            tool_input=tool_input,
            tool_output=response_dict,
            agent_name=agent_name,
            error=False,
            transaction=transaction,
            linking_metadata=linking_metadata,
        )
        if tool_event_dict:
            tool_event_dict["duration"] = ft.duration * 1000
            transaction.record_custom_event("LlmTool", tool_event_dict)
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return tool_output


def _extract_tool_response_dict(tool_output):
    """Return the dict at content.parts[*].function_response.response, or None."""
    try:
        parts = tool_output.content.parts
        for part in parts:
            function_response = getattr(part, "function_response", None)
            if function_response is not None:
                return getattr(function_response, "response", None)
    except (AttributeError, TypeError):
        pass
    return None


def _construct_base_tool_event_dict(
    tool_name, tool_id, run_id, tool_input, tool_output, agent_name, error, transaction, linking_metadata
):
    try:
        settings = transaction.settings or global_settings()

        tool_event_dict = {
            "id": tool_id,
            "run_id": run_id,
            "name": tool_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "agent_name": agent_name,
            "vendor": "google_adk",
            "ingest_source": "Python",
        }
        if error:
            tool_event_dict["error"] = True

        if settings.ai_monitoring.record_content.enabled:
            tool_event_dict["input"] = str(tool_input) if tool_input else None
            tool_event_dict["output"] = str(tool_output) if tool_output else None

        tool_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        tool_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return tool_event_dict


def instrument_googleadk_flows_llm_flows_functions(module):
    if hasattr(module, "_execute_single_function_call_async"):
        wrap_function_wrapper(module, "_execute_single_function_call_async", wrap__execute_single_function_call_async)
