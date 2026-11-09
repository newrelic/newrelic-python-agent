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
from newrelic.api.time_trace import current_trace, get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.llm_utils import _get_llm_metadata
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.context import ContextOf

_logger = logging.getLogger(__name__)
AGENT_FRAMEWORK_VERSION = get_package_version("agent-framework")
AGENT_EVENT_FAILURE_LOG_MESSAGE = "Exception occurred in Microsoft Agent Framework instrumentation: Failed to record Agent LLM events. Please report this issue to New Relic Support."
TOOL_EVENT_FAILURE_LOG_MESSAGE = "Exception occurred in Microsoft Agent Framework instrumentation: Failed to record Tool LLM events. Please report this issue to New Relic Support."
TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE = "Exception occurred in Microsoft Agent Framework instrumentation: Failed to extract tool information. If the issue persists, report this issue to New Relic Support."
BEDROCK_CONTEXT_FAILURE_MESSAGE = "Failed to attach existing trace to request in agent_framework_bedrock."
TOOL_CONTEXT_FAILURE_MESSAGE = "Failed to attach existing trace to FunctionTool call agent_framework."

# ======================
# Agents Instrumentation
# ======================


def wrap_Agent_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings
    if not settings or not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("MicrosoftAgentFramework", AGENT_FRAMEWORK_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(instance, "name", "agent") or "agent"
    function_trace_name = f"run/{agent_name}"
    agentic_subcomponent_data = {"type": "APM-AI_AGENT", "name": agent_name}

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/MicrosoftAgentFramework")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))
    # Tag the trace so tools invoked during this run can find their invoking agent.
    ft._nr_agentframework_agent_name = agent_name

    linking_metadata = get_trace_linking_metadata()
    agent_id = str(uuid.uuid4())

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        _record_agent_event(
            transaction=transaction,
            ft=ft,
            linking_metadata=linking_metadata,
            agent_name=agent_name,
            agent_id=agent_id,
            error=True,
        )
        raise

    # Handle streaming case by registering a cleanup hook, as proxying the response object is very difficult.
    # Known limitation: the hook does not fire if the stream is closed or garbage collected before completing.
    if hasattr(return_val, "with_cleanup_hook"):
        try:
            return_val.with_cleanup_hook(
                _Agent_run_streaming_cleanup_hook(
                    transaction=transaction,
                    stream=return_val,
                    ft=ft,
                    linking_metadata=linking_metadata,
                    agent_name=agent_name,
                    agent_id=agent_id,
                )
            )
            return return_val
        except Exception:
            # The underlying Agent.run() call succeeded, so don't mark the span as errored.
            _logger.warning(AGENT_EVENT_FAILURE_LOG_MESSAGE, exc_info=True)
            ft.__exit__(None, None, None)
            return return_val

    # Non-streaming run() returns an awaitable. Return a coroutine that awaits it and records the
    # LlmAgent event on completion.
    return _wrap_Agent_run_coroutine(return_val, transaction, ft, linking_metadata, agent_name, agent_id)


async def _wrap_Agent_run_coroutine(coro, transaction, ft, linking_metadata, agent_name, agent_id):
    # Wrap the corountine returned by Agent.run() and record events when it completes.
    try:
        return_val = await coro
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        _record_agent_event(
            transaction=transaction,
            ft=ft,
            linking_metadata=linking_metadata,
            agent_name=agent_name,
            agent_id=agent_id,
            error=True,
        )
        raise

    ft.__exit__(None, None, None)
    _record_agent_event(
        transaction=transaction, ft=ft, linking_metadata=linking_metadata, agent_name=agent_name, agent_id=agent_id
    )
    return return_val


def _Agent_run_streaming_cleanup_hook(*, transaction, stream, ft, linking_metadata, agent_name, agent_id):
    def _nr_streaming_cleanup_hook():
        try:
            errored = getattr(stream, "_stream_error", None) is not None
            if errored:
                ft.notice_error(attributes={"agent_id": agent_id})
                ft.__exit__(*sys.exc_info())
            else:
                ft.__exit__(None, None, None)

            _record_agent_event(
                transaction=transaction,
                ft=ft,
                linking_metadata=linking_metadata,
                agent_name=agent_name,
                agent_id=agent_id,
                error=errored,
            )
        except Exception:
            _logger.warning(AGENT_EVENT_FAILURE_LOG_MESSAGE, exc_info=True)

    return _nr_streaming_cleanup_hook


def _record_agent_event(*, transaction, ft, linking_metadata, agent_name, agent_id, error=False):
    if not transaction:
        return
    try:
        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "duration": ft.duration * 1000,
            "vendor": "agentframework",
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
        if error:
            agent_event_dict["error"] = True
        transaction.record_custom_event("LlmAgent", agent_event_dict)
    except Exception:
        _logger.warning(AGENT_EVENT_FAILURE_LOG_MESSAGE, exc_info=True)


# =====================
# Tools Instrumentation
# =====================


async def wrap_FunctionTool_invoke(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings
    if not settings or not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    transaction.add_ml_model_info("MicrosoftAgentFramework", AGENT_FRAMEWORK_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_name = getattr(instance, "name", "tool") or "tool"
    run_id = ""
    tool_input = None
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        run_id = bound_args.get("tool_call_id") or ""
        tool_input = bound_args.get("arguments")
    except Exception:
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)

    ft = FunctionTrace(name=f"invoke/{tool_name}", group="Llm/tool/MicrosoftAgentFramework")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps({"type": "APM-AI_TOOL", "name": tool_name}))
    agent_name = _get_parent_agent_name(ft.parent)
    linking_metadata = get_trace_linking_metadata()
    tool_id = str(uuid.uuid4())

    try:
        tool_output = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"tool_id": tool_id})
        ft.__exit__(*sys.exc_info())
        _record_tool_event(
            transaction=transaction,
            ft=ft,
            linking_metadata=linking_metadata,
            tool_name=tool_name,
            tool_id=tool_id,
            run_id=run_id,
            tool_input=tool_input,
            tool_output=None,
            agent_name=agent_name,
            error=True,
        )
        raise

    ft.__exit__(None, None, None)
    tool_output_str = _extract_tool_response_str(tool_output)
    _record_tool_event(
        transaction=transaction,
        ft=ft,
        linking_metadata=linking_metadata,
        tool_name=tool_name,
        tool_id=tool_id,
        run_id=run_id,
        tool_input=tool_input,
        tool_output=tool_output_str,
        agent_name=agent_name,
    )
    return tool_output


def _get_parent_agent_name(trace):
    # Walk up the trace tree to find the name of the nearest enclosing LlmAgent trace.
    # Agent Framework does not pass the invoking agent to tools, so we rely on the tag set in wrap_Agent_run.
    try:
        while trace is not None:
            agent_name = getattr(trace, "_nr_agentframework_agent_name", None)
            if agent_name:
                return agent_name
            trace = trace.parent
    except Exception:
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)
    return None


def _extract_tool_response_str(tool_output):
    """Extract a text string from a FunctionTool.invoke() result (a list[Content]), else str()."""
    try:
        if isinstance(tool_output, (list, tuple)):
            text = "\n".join(content.text or "" for content in tool_output if getattr(content, "type", None) == "text")
            return text or str(tool_output)
        return str(tool_output) if tool_output is not None else None
    except Exception:
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)
        return None


def _record_tool_event(
    *,
    transaction,
    ft,
    linking_metadata,
    tool_name,
    tool_id,
    run_id,
    tool_input,
    tool_output,
    agent_name=None,
    error=False,
):
    if not transaction:
        return
    try:
        settings = transaction.settings

        tool_event_dict = {
            "id": tool_id,
            "run_id": run_id,
            "name": tool_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": "agentframework",
            "ingest_source": "Python",
            "duration": ft.duration * 1000,
        }
        if error:
            tool_event_dict["error"] = True
        if agent_name:
            tool_event_dict["agent_name"] = agent_name

        if settings and settings.ai_monitoring.record_content.enabled:
            tool_event_dict["input"] = str(tool_input) if tool_input else None
            tool_event_dict["output"] = str(tool_output) if tool_output else None

        tool_event_dict.update(_get_llm_metadata(transaction))
        transaction.record_custom_event("LlmTool", tool_event_dict)
    except Exception:
        _logger.warning(TOOL_EVENT_FAILURE_LOG_MESSAGE, exc_info=True)


# ===================
# Context Propagation
# ===================


def wrap_FunctionTool__invoke_function(wrapped, instance, args, kwargs):
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    # Attach the current trace to the request so we can resume it inside the asyncio.to_thread call
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        bound_args["call_kwargs"]["_nr_trace_id"] = trace.thread_id
    except Exception:
        _logger.debug(TOOL_CONTEXT_FAILURE_MESSAGE)

    return wrapped(*args, **kwargs)


def wrap_FunctionTool_call(wrapped, instance, args, kwargs):
    # Pop the current trace out of the request object and resume it on this thread
    try:
        trace_cache_id = kwargs.pop("_nr_trace_id", None)
    except Exception:
        trace_cache_id = None

    if trace_cache_id:
        with ContextOf(trace_cache_id=trace_cache_id, strict=False):
            return wrapped(*args, **kwargs)
    else:
        return wrapped(*args, **kwargs)


def wrap_BedrockChatClient__invoke_converse(wrapped, instance, args, kwargs):
    # Pop the current trace out of the request object and resume it on this thread
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        request = bound_args["request"]
        trace_cache_id = request.pop("_nr_trace_id", None)
    except Exception:
        trace_cache_id = None

    if trace_cache_id:
        with ContextOf(trace_cache_id=trace_cache_id, strict=False):
            return wrapped(*args, **kwargs)
    else:
        return wrapped(*args, **kwargs)


def wrap_BedrockChatClient__prepare_options(wrapped, instance, args, kwargs):
    request = wrapped(*args, **kwargs)

    trace = current_trace()
    if not trace:
        return request

    # Attach the current trace to the request so we can resume it inside the asyncio.to_thread call
    try:
        request["_nr_trace_id"] = trace.thread_id
    except Exception:
        _logger.debug(BEDROCK_CONTEXT_FAILURE_MESSAGE)

    return request


def instrument_agent_framework__agents(module):
    if hasattr(module, "Agent"):
        if hasattr(module.Agent, "run"):
            wrap_function_wrapper(module, "Agent.run", wrap_Agent_run)


def instrument_agent_framework__tools(module):
    if hasattr(module, "FunctionTool"):
        if hasattr(module.FunctionTool, "invoke"):
            wrap_function_wrapper(module, "FunctionTool.invoke", wrap_FunctionTool_invoke)
        if hasattr(module.FunctionTool, "_invoke_function") and hasattr(module.FunctionTool, "__call__"):  # noqa: B004
            wrap_function_wrapper(module, "FunctionTool._invoke_function", wrap_FunctionTool__invoke_function)
            wrap_function_wrapper(module, "FunctionTool.__call__", wrap_FunctionTool_call)


def instrument_agent_framework_bedrock__chat_client(module):
    if (
        hasattr(module, "BedrockChatClient")
        and hasattr(module.BedrockChatClient, "_invoke_converse")
        and hasattr(module.BedrockChatClient, "_prepare_options")
    ):
        # Only wrap context propagation wrappers if both endpoints are present.
        wrap_function_wrapper(module, "BedrockChatClient._invoke_converse", wrap_BedrockChatClient__invoke_converse)
        wrap_function_wrapper(module, "BedrockChatClient._prepare_options", wrap_BedrockChatClient__prepare_options)
