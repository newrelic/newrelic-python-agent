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

import contextvars
import json
import logging
import sys
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.llm_utils import AsyncGeneratorProxy
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings
from newrelic.core.context import ContextOf

# Check for the presence of the autogen-core, autogen-agentchat, or autogen-ext package as they should all have the
# same version and one or multiple could be installed
AUTOGEN_VERSION = (
    get_package_version("autogen-core")
    or get_package_version("autogen-agentchat")
    or get_package_version("autogen-ext")
)


# ContextVar used to propagate trace context to tool functions that may run on thread pool threads.
# This allows nested agents created inside tools to find the parent trace.
_nr_tool_parent_trace = contextvars.ContextVar("_nr_tool_parent_trace", default=None)

# Flag to indicate we're inside wrap_on_messages, so on_messages_stream can skip
# creating a duplicate agent FT (on_messages internally calls on_messages_stream).
_nr_in_on_messages = contextvars.ContextVar("_nr_in_on_messages", default=False)

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


async def wrap_on_messages(wrapped, instance, args, kwargs):
    """Wrap on_messages (a regular async method) with an agent FunctionTrace.

    on_messages is called by run() and internally iterates on_messages_stream.
    Since on_messages is awaited (not an async generator), the FT can stay open
    for the full execution, making tool FTs proper children of this agent FT.
    """
    transaction = current_transaction()
    if not transaction:
        # When a tool calls an inner agent on a different thread, NR's thread-local context is lost.
        # The ContextVar is propagated by asyncio, so we can recover the parent trace from it.
        parent_trace = _nr_tool_parent_trace.get(None)
        if parent_trace:
            with ContextOf(trace=parent_trace):
                return await _on_messages_instrumented(wrapped, instance, args, kwargs)
        return await wrapped(*args, **kwargs)

    return await _on_messages_instrumented(wrapped, instance, args, kwargs)


async def _on_messages_instrumented(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Autogen", AUTOGEN_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(instance, "name", "agent")
    agent_id = str(uuid.uuid4())
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"

    agentic_subcomponent_data = {"type": "APM-AI_AGENT", "name": agent_name}

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/Autogen")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))

    # Set flag so on_messages_stream (called internally) skips creating a duplicate agent FT.
    token = _nr_in_on_messages.set(True)

    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmAgent", agent_event_dict)
        raise
    finally:
        _nr_in_on_messages.reset(token)

    ft.__exit__(None, None, None)

    agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
    agent_event_dict["duration"] = ft.duration * 1000
    transaction.record_custom_event("LlmAgent", agent_event_dict)

    return return_val


def wrap_on_messages_stream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        # When a tool calls an inner agent on a different thread, NR's thread-local context is lost.
        # The ContextVar is propagated by asyncio, so we can recover the parent trace from it.
        parent_trace = _nr_tool_parent_trace.get(None)
        if parent_trace:
            with ContextOf(trace=parent_trace):
                return _on_messages_stream_instrumented(wrapped, instance, args, kwargs)
        return wrapped(*args, **kwargs)

    return _on_messages_stream_instrumented(wrapped, instance, args, kwargs)


def _on_messages_stream_instrumented(wrapped, instance, args, kwargs):
    """Wrap on_messages_stream with an agent FT.

    on_messages_stream returns an AsyncGenerator. When called from on_messages
    (the run() path), the agent FT is already created by wrap_on_messages, so
    we skip creating a duplicate here. When called directly (the run_stream()
    path), the agent FT stays open and is exited when the generator finishes
    via AsyncGeneratorProxy callbacks, keeping tools as children of the agent.
    """
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # If we're already inside wrap_on_messages, skip the agent FT here to avoid
    # a duplicate span. The on_messages wrapper owns the agent FT in that case.
    if _nr_in_on_messages.get(False):
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Autogen", AUTOGEN_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(instance, "name", "agent")
    agent_id = str(uuid.uuid4())
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"

    agentic_subcomponent_data = {"type": "APM-AI_AGENT", "name": agent_name}

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/Autogen")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmAgent", agent_event_dict)
        raise

    # Wrap the async generator with a proxy that keeps the agent FT open during
    # iteration. The FT is exited when the generator finishes (StopAsyncIteration)
    # or encounters an error. This ensures tool FTs created during iteration are
    # children of the agent FT, not siblings.
    proxied_return_val = _AutogenAsyncGeneratorProxy(return_val, _record_stream_agent_event, _handle_stream_agent_error)
    proxied_return_val._nr_ft = ft
    proxied_return_val._nr_agent_name = agent_name
    proxied_return_val._nr_agent_id = agent_id

    return proxied_return_val


class _AutogenAsyncGeneratorProxy(AsyncGeneratorProxy):
    """AsyncGeneratorProxy subclass that also exits the agent FT on aclose() and __del__.

    When the stream is fully consumed, the base class fires the
    StopAsyncIteration callback which exits the FT.  When the user
    calls aclose() explicitly, the override below exits the FT.

    When the user breaks out of an outer ``async for`` (e.g. run_stream()),
    Python throws GeneratorExit into the outer generator, but the inner
    async generator's aclose() cannot be awaited in that context.  In
    CPython, once the outer generator frame is torn down the proxy's
    reference count drops to zero and __del__ fires synchronously,
    giving us a last-resort opportunity to exit the agent FT.
    """

    async def aclose(self):
        try:
            return await self.__wrapped__.aclose()
        finally:
            _exit_stream_agent_ft(self)

    def __del__(self):
        _exit_stream_agent_ft(self)


def _exit_stream_agent_ft(proxy, error=False):
    """Exit the agent FT stored on the proxy and record the LlmAgent event.

    Guards against double-exit: if the FT was already exited (e.g. by
    StopAsyncIteration firing before aclose), this is a no-op.
    """
    ft = getattr(proxy, "_nr_ft", None)
    if not ft or ft.exited:
        return

    agent_name = getattr(proxy, "_nr_agent_name", "agent")
    agent_id = getattr(proxy, "_nr_agent_id", None)

    if error:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
    else:
        ft.__exit__(None, None, None)

    transaction = current_transaction()
    if not transaction:
        return

    try:
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        agent_event_dict["duration"] = ft.duration * 1000
        if error:
            agent_event_dict["error"] = True
        transaction.record_custom_event("LlmAgent", agent_event_dict)
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)


def _record_stream_agent_event(proxy, _transaction):
    """Callback for AsyncGeneratorProxy when the stream finishes normally (StopAsyncIteration)."""
    _exit_stream_agent_ft(proxy, error=False)


def _handle_stream_agent_error(proxy, _transaction):
    """Callback for AsyncGeneratorProxy when the stream encounters an error."""
    _exit_stream_agent_ft(proxy, error=True)


def _get_llm_metadata(transaction):
    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}
    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def _extract_tool_output(return_val, tool_name):
    try:
        output = getattr(return_val[1], "content", None)
        return output
    except Exception:
        _logger.warning("Unable to parse tool output value from %s. Omitting output from LlmTool event.", tool_name)
        return None


def _construct_base_tool_event_dict(bound_args, tool_call_data, tool_id, transaction, settings):
    try:
        _input = getattr(tool_call_data, "arguments", None)
        tool_input = str(_input) if _input else None
        run_id = getattr(tool_call_data, "id", None)
        tool_name = getattr(tool_call_data, "name", "tool")
        agent_name = bound_args.get("agent_name")
        linking_metadata = get_trace_linking_metadata()

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
    except Exception:
        tool_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return tool_event_dict


def _construct_base_agent_event_dict(agent_name, agent_id, transaction):
    try:
        linking_metadata = get_trace_linking_metadata()

        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": "autogen",
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        agent_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return agent_event_dict


async def wrap__execute_tool_call(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Autogen", AUTOGEN_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_id = str(uuid.uuid4())
    bound_args = bind_args(wrapped, args, kwargs)
    tool_call_data = bound_args.get("tool_call")
    tool_event_dict = _construct_base_tool_event_dict(bound_args, tool_call_data, tool_id, transaction, settings)
    tool_name = getattr(tool_call_data, "name", "tool")
    func_name = callable_name(wrapped)

    agentic_subcomponent_data = {"type": "APM-AI_TOOL", "name": tool_name}

    ft = FunctionTrace(name=f"{func_name}/{tool_name}", group="Llm/tool/Autogen")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))

    # Store the tool's trace in a ContextVar so that nested agents created inside tool functions
    # (which may run on thread pool threads) can find the parent trace.
    _nr_tool_parent_trace.set(ft)

    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"tool_id": tool_id})
        ft.__exit__(*sys.exc_info())
        # If we hit an exception, append the error attribute and duration from the exited function trace
        tool_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmTool", tool_event_dict)
        raise

    ft.__exit__(None, None, None)
    tool_event_dict.update({"duration": ft.duration * 1000})

    # If the tool was executed successfully, we can grab the tool output from the result
    tool_output = _extract_tool_output(return_val, tool_name)
    if settings.ai_monitoring.record_content.enabled:
        tool_event_dict.update({"output": tool_output})

    transaction.record_custom_event("LlmTool", tool_event_dict)

    return return_val


def instrument_autogen_agentchat_agents__assistant_agent(module):
    if hasattr(module, "AssistantAgent"):
        if hasattr(module.AssistantAgent, "on_messages"):
            wrap_function_wrapper(module, "AssistantAgent.on_messages", wrap_on_messages)
        if hasattr(module.AssistantAgent, "on_messages_stream"):
            wrap_function_wrapper(module, "AssistantAgent.on_messages_stream", wrap_on_messages_stream)
        if hasattr(module.AssistantAgent, "_execute_tool_call"):
            wrap_function_wrapper(module, "AssistantAgent._execute_tool_call", wrap__execute_tool_call)


def instrument_autogen_ext_tools_mcp__base(module):
    if hasattr(module, "McpToolAdapter"):
        if hasattr(module.McpToolAdapter, "from_server_params"):
            wrap_function_wrapper(module, "McpToolAdapter.from_server_params", wrap_from_server_params)
