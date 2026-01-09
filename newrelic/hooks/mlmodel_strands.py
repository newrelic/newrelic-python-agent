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
import sys
import uuid

from newrelic.api.error_trace import ErrorTraceWrapper
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace, get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.llm_utils import _get_llm_metadata
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings
from newrelic.core.context import ContextOf

_logger = logging.getLogger(__name__)
STRANDS_VERSION = get_package_version("strands-agents")

RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Strands instrumentation: Failed to record LLM events. Please report this issue to New Relic Support."
TOOL_OUTPUT_FAILURE_LOG_MESSAGE = "Exception occurred in Strands instrumentation: Failed to record output of tool call. Please report this issue to New Relic Support."
AGENT_EVENT_FAILURE_LOG_MESSAGE = "Exception occurred in Strands instrumentation: Failed to record agent data. Please report this issue to New Relic Support."
TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE = "Exception occurred in Strands instrumentation: Failed to extract tool information. If the issue persists, report this issue to New Relic support.\n"


def wrap_agent__call__(wrapped, instance, args, kwargs):
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        # Make a copy of the invocation state before we mutate it
        if "invocation_state" in bound_args:
            invocation_state = bound_args["invocation_state"] = dict(bound_args["invocation_state"] or {})

            # Attempt to save the current transaction context into the invocation state dictionary
            invocation_state["_nr_transaction"] = trace
    except Exception:
        return wrapped(*args, **kwargs)
    else:
        return wrapped(**bound_args)


async def wrap_agent_invoke_async(wrapped, instance, args, kwargs):
    # If there's already a transaction, don't propagate anything here
    if current_transaction():
        return await wrapped(*args, **kwargs)

    try:
        # Grab the trace context we should be running under and pass it to ContextOf
        bound_args = bind_args(wrapped, args, kwargs)
        invocation_state = bound_args["invocation_state"] or {}
        trace = invocation_state.pop("_nr_transaction", None)
    except Exception:
        return await wrapped(*args, **kwargs)

    # If we find a transaction to propagate, use it. Otherwise, just call wrapped.
    if trace:
        with ContextOf(trace=trace):
            return await wrapped(*args, **kwargs)
    else:
        return await wrapped(*args, **kwargs)


def wrap_stream_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Strands", STRANDS_VERSION)
    transaction._add_agent_attribute("llm", True)

    func_name = callable_name(wrapped)
    agent_name = getattr(instance, "name", "agent")
    function_trace_name = f"{func_name}/{agent_name}"

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/Strands")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    agent_id = str(uuid.uuid4())

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        raise

    # For streaming responses, wrap with proxy and attach metadata
    try:
        # For streaming responses, wrap with proxy and attach metadata
        proxied_return_val = AsyncGeneratorProxy(
            return_val, _record_agent_event_on_stop_iteration, _handle_agent_streaming_completion_error
        )
        proxied_return_val._nr_ft = ft
        proxied_return_val._nr_metadata = linking_metadata
        proxied_return_val._nr_strands_attrs = {"agent_name": agent_name, "agent_id": agent_id}
        return proxied_return_val
    except Exception:
        # If proxy creation fails, clean up the function trace and return original value
        ft.__exit__(*sys.exc_info())
        return return_val


def _record_agent_event_on_stop_iteration(self, transaction):
    if hasattr(self, "_nr_ft"):
        # Use saved linking metadata to maintain correct span association
        linking_metadata = self._nr_metadata or get_trace_linking_metadata()
        self._nr_ft.__exit__(None, None, None)

        try:
            strands_attrs = getattr(self, "_nr_strands_attrs", {})

            # If there are no strands attrs exit early as there's no data to record.
            if not strands_attrs:
                return

            agent_name = strands_attrs.get("agent_name", "agent")
            agent_id = strands_attrs.get("agent_id")
            agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction, linking_metadata)
            agent_event_dict["duration"] = self._nr_ft.duration * 1000
            transaction.record_custom_event("LlmAgent", agent_event_dict)

        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            # Clear cached data to prevent memory leaks and duplicate reporting
            if hasattr(self, "_nr_strands_attrs"):
                self._nr_strands_attrs.clear()


def _record_tool_event_on_stop_iteration(self, transaction):
    if hasattr(self, "_nr_ft"):
        # Use saved linking metadata to maintain correct span association
        linking_metadata = self._nr_metadata or get_trace_linking_metadata()
        self._nr_ft.__exit__(None, None, None)

        try:
            strands_attrs = getattr(self, "_nr_strands_attrs", {})

            # If there are no strands attrs exit early as there's no data to record.
            if not strands_attrs:
                return

            try:
                tool_results = strands_attrs.get("tool_results", [])
            except Exception:
                tool_results = None
                _logger.warning(TOOL_OUTPUT_FAILURE_LOG_MESSAGE, exc_info=True)

            tool_event_dict = _construct_base_tool_event_dict(
                strands_attrs, tool_results, transaction, linking_metadata
            )
            tool_event_dict["duration"] = self._nr_ft.duration * 1000
            transaction.record_custom_event("LlmTool", tool_event_dict)

        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            # Clear cached data to prevent memory leaks and duplicate reporting
            if hasattr(self, "_nr_strands_attrs"):
                self._nr_strands_attrs.clear()


def _construct_base_tool_event_dict(strands_attrs, tool_results, transaction, linking_metadata):
    try:
        try:
            tool_output = tool_results[-1]["content"][0] if tool_results else None
            error = tool_results[-1]["status"] == "error"
        except Exception:
            tool_output = None
            error = False
            _logger.warning(TOOL_OUTPUT_FAILURE_LOG_MESSAGE, exc_info=True)

        tool_name = strands_attrs.get("tool_name", "tool")
        tool_id = strands_attrs.get("tool_id")
        run_id = strands_attrs.get("run_id")
        tool_input = strands_attrs.get("tool_input")
        agent_name = strands_attrs.get("agent_name", "agent")
        settings = transaction.settings or global_settings()

        tool_event_dict = {
            "id": tool_id,
            "run_id": run_id,
            "name": tool_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "agent_name": agent_name,
            "vendor": "strands",
            "ingest_source": "Python",
        }
        # Set error flag if the status shows an error was caught,
        # it will be reported further down in the instrumentation.
        if error:
            tool_event_dict["error"] = True

        if settings.ai_monitoring.record_content.enabled:
            tool_event_dict["input"] = tool_input
            # In error cases, the output will hold the error message
            tool_event_dict["output"] = tool_output
        tool_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        tool_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return tool_event_dict


def _construct_base_agent_event_dict(agent_name, agent_id, transaction, linking_metadata):
    try:
        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": "strands",
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        _logger.warning(AGENT_EVENT_FAILURE_LOG_MESSAGE, exc_info=True)
        agent_event_dict = {}

    return agent_event_dict


def _handle_agent_streaming_completion_error(self, transaction):
    if hasattr(self, "_nr_ft"):
        strands_attrs = getattr(self, "_nr_strands_attrs", {})

        # If there are no strands attrs exit early as there's no data to record.
        if not strands_attrs:
            self._nr_ft.__exit__(*sys.exc_info())
            return

        # Use saved linking metadata to maintain correct span association
        linking_metadata = self._nr_metadata or get_trace_linking_metadata()

        try:
            agent_name = strands_attrs.get("agent_name", "agent")
            agent_id = strands_attrs.get("agent_id")

            # Notice the error on the function trace
            self._nr_ft.notice_error(attributes={"agent_id": agent_id})
            self._nr_ft.__exit__(*sys.exc_info())

            # Create error event
            agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction, linking_metadata)
            agent_event_dict.update({"duration": self._nr_ft.duration * 1000, "error": True})
            transaction.record_custom_event("LlmAgent", agent_event_dict)

        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            # Clear cached data to prevent memory leaks
            if hasattr(self, "_nr_strands_attrs"):
                self._nr_strands_attrs.clear()


def _handle_tool_streaming_completion_error(self, transaction):
    if hasattr(self, "_nr_ft"):
        strands_attrs = getattr(self, "_nr_strands_attrs", {})

        # If there are no strands attrs exit early as there's no data to record.
        if not strands_attrs:
            self._nr_ft.__exit__(*sys.exc_info())
            return

        # Use saved linking metadata to maintain correct span association
        linking_metadata = self._nr_metadata or get_trace_linking_metadata()

        try:
            tool_id = strands_attrs.get("tool_id")

            # We expect this to never have any output since this is an error case,
            # but if it does we will report it.
            try:
                tool_results = strands_attrs.get("tool_results", [])
            except Exception:
                tool_results = None
                _logger.warning(TOOL_OUTPUT_FAILURE_LOG_MESSAGE, exc_info=True)

            # Notice the error on the function trace
            self._nr_ft.notice_error(attributes={"tool_id": tool_id})
            self._nr_ft.__exit__(*sys.exc_info())

            # Create error event
            tool_event_dict = _construct_base_tool_event_dict(
                strands_attrs, tool_results, transaction, linking_metadata
            )
            tool_event_dict["duration"] = self._nr_ft.duration * 1000
            # Ensure error flag is set to True in case the tool_results did not indicate an error
            if "error" not in tool_event_dict:
                tool_event_dict["error"] = True

            transaction.record_custom_event("LlmTool", tool_event_dict)

        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            # Clear cached data to prevent memory leaks
            if hasattr(self, "_nr_strands_attrs"):
                self._nr_strands_attrs.clear()


def wrap_tool_executor__stream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Strands", STRANDS_VERSION)
    transaction._add_agent_attribute("llm", True)

    # Grab tool data
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        agent_name = getattr(bound_args.get("agent"), "name", "agent")
        tool_use = bound_args.get("tool_use", {})

        run_id = tool_use.get("toolUseId", "")
        tool_name = tool_use.get("name", "tool")
        _input = tool_use.get("input")
        tool_input = str(_input) if _input else None
        tool_results = bound_args.get("tool_results", [])
    except Exception:
        tool_name = "tool"
        _logger.warning(TOOL_EXTRACTOR_FAILURE_LOG_MESSAGE, exc_info=True)

    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{tool_name}"

    ft = FunctionTrace(name=function_trace_name, group="Llm/tool/Strands")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    tool_id = str(uuid.uuid4())

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        raise

    try:
        # Wrap return value with proxy and attach metadata for later access
        proxied_return_val = AsyncGeneratorProxy(
            return_val, _record_tool_event_on_stop_iteration, _handle_tool_streaming_completion_error
        )
        proxied_return_val._nr_ft = ft
        proxied_return_val._nr_metadata = linking_metadata
        proxied_return_val._nr_strands_attrs = {
            "tool_results": tool_results,
            "tool_name": tool_name,
            "tool_id": tool_id,
            "run_id": run_id,
            "tool_input": tool_input,
            "agent_name": agent_name,
        }
        return proxied_return_val
    except Exception:
        # If proxy creation fails, clean up the function trace and return original value
        ft.__exit__(*sys.exc_info())
        return return_val


class AsyncGeneratorProxy(ObjectProxy):
    def __init__(self, wrapped, on_stop_iteration, on_error):
        super().__init__(wrapped)
        self._nr_on_stop_iteration = on_stop_iteration
        self._nr_on_error = on_error

    def __aiter__(self):
        self._nr_wrapped_iter = self.__wrapped__.__aiter__()
        return self

    async def __anext__(self):
        transaction = current_transaction()
        if not transaction:
            return await self._nr_wrapped_iter.__anext__()

        return_val = None
        try:
            return_val = await self._nr_wrapped_iter.__anext__()
        except StopAsyncIteration:
            self._nr_on_stop_iteration(self, transaction)
            raise
        except Exception:
            self._nr_on_error(self, transaction)
            raise
        return return_val

    async def aclose(self):
        return await super().aclose()


def wrap_ToolRegister_register_tool(wrapped, instance, args, kwargs):
    try:
        from strands.tools.decorator import DecoratedFunctionTool
    except ImportError:
        # If we can't import this to check for double wrapping, return early
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
    except Exception:
        return wrapped(*args, **kwargs)

    tool = bound_args.get("tool")

    # Ensure we don't double capture exceptions by not touching DecoratedFunctionTool instances here.
    # Those should be captured with specific instrumentation that properly handles the thread boundaries.
    if hasattr(tool, "stream") and not isinstance(tool, DecoratedFunctionTool):
        tool.stream = ErrorTraceWrapper(tool.stream)

    return wrapped(*args, **kwargs)


def wrap_bedrock_model_stream(wrapped, instance, args, kwargs):
    """Stores trace context on the messages argument to be retrieved by the _stream() instrumentation."""
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    settings = trace.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
    except Exception:
        return wrapped(*args, **kwargs)

    if "messages" in bound_args and isinstance(bound_args["messages"], list):
        bound_args["messages"].append({"newrelic_trace": trace})

    return wrapped(*args, **kwargs)


def wrap_bedrock_model__stream(wrapped, instance, args, kwargs):
    """Retrieves trace context stored on the messages argument and propagates it to the new thread."""
    try:
        bound_args = bind_args(wrapped, args, kwargs)
    except Exception:
        return wrapped(*args, **kwargs)

    if (
        "messages" in bound_args
        and isinstance(bound_args["messages"], list)
        and bound_args["messages"]  # non-empty list
        and "newrelic_trace" in bound_args["messages"][-1]
    ):
        trace_message = bound_args["messages"].pop()
        with ContextOf(trace=trace_message["newrelic_trace"]):
            return wrapped(*args, **kwargs)

    return wrapped(*args, **kwargs)


def wrap_decorated_function_tool__wrap_tool_result(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction:
        # notice_error will handle pulling from sys.exc_info() if there's an active exception.
        transaction.notice_error()

    return wrapped(*args, **kwargs)


def instrument_strands_agent_agent(module):
    if hasattr(module, "Agent"):
        if hasattr(module.Agent, "__call__"):  # noqa: B004
            wrap_function_wrapper(module, "Agent.__call__", wrap_agent__call__)
        if hasattr(module.Agent, "invoke_async"):
            wrap_function_wrapper(module, "Agent.invoke_async", wrap_agent_invoke_async)
        if hasattr(module.Agent, "stream_async"):
            wrap_function_wrapper(module, "Agent.stream_async", wrap_stream_async)


def instrument_strands_multiagent_graph(module):
    if hasattr(module, "Graph"):
        if hasattr(module.Graph, "__call__"):  # noqa: B004
            wrap_function_wrapper(module, "Graph.__call__", wrap_agent__call__)
        if hasattr(module.Graph, "invoke_async"):
            wrap_function_wrapper(module, "Graph.invoke_async", wrap_agent_invoke_async)


def instrument_strands_multiagent_swarm(module):
    if hasattr(module, "Swarm"):
        if hasattr(module.Swarm, "__call__"):  # noqa: B004
            wrap_function_wrapper(module, "Swarm.__call__", wrap_agent__call__)
        if hasattr(module.Swarm, "invoke_async"):
            wrap_function_wrapper(module, "Swarm.invoke_async", wrap_agent_invoke_async)


def instrument_strands_tools_decorator(module):
    # This instrumentation only exists to pass trace context due to bedrock models using a separate thread.
    if hasattr(module, "DecoratedFunctionTool") and hasattr(module.DecoratedFunctionTool, "_wrap_tool_result"):
        wrap_function_wrapper(
            module, "DecoratedFunctionTool._wrap_tool_result", wrap_decorated_function_tool__wrap_tool_result
        )


def instrument_strands_tools_executors__executor(module):
    if hasattr(module, "ToolExecutor"):
        if hasattr(module.ToolExecutor, "_stream"):
            wrap_function_wrapper(module, "ToolExecutor._stream", wrap_tool_executor__stream)


def instrument_strands_tools_registry(module):
    if hasattr(module, "ToolRegistry"):
        if hasattr(module.ToolRegistry, "register_tool"):
            wrap_function_wrapper(module, "ToolRegistry.register_tool", wrap_ToolRegister_register_tool)


def instrument_strands_models_bedrock(module):
    # This instrumentation only exists to pass trace context due to bedrock models using a separate thread.
    if hasattr(module, "BedrockModel"):
        if hasattr(module.BedrockModel, "stream"):
            wrap_function_wrapper(module, "BedrockModel.stream", wrap_bedrock_model_stream)
        if hasattr(module.BedrockModel, "_stream"):
            wrap_function_wrapper(module, "BedrockModel._stream", wrap_bedrock_model__stream)
