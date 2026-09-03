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
from newrelic.core.config import global_settings
from newrelic.core.context import ContextOf

_logger = logging.getLogger(__name__)
AGENT_FRAMEWORK_VERSION = get_package_version("agent-framework")
AGENT_EVENT_FAILURE_LOG_MESSAGE = "Exception occurred in Microsoft Agent Framework instrumentation: Failed to record Agent LLM events. Please report this issue to New Relic Support."
BEDROCK_CONTEXT_FAILURE_MESSAGE = "Failed to attach existing trace to request in agent_framework_bedrock."

# ======================
# Agents Instrumentation
# ======================


def wrap_Agent_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("MicrosoftAgentFramework", AGENT_FRAMEWORK_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(instance, "name", "agent") or "agent"
    function_trace_name = f"run/{agent_name}"
    agentic_subcomponent_data = {"type": "APM-AI_AGENT", "name": agent_name}

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/MicrosoftAgentFramework")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))

    linking_metadata = get_trace_linking_metadata()
    agent_id = str(uuid.uuid4())

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.__exit__(*sys.exc_info())
        raise

    # Handle streaming case by registering a cleanup hook, as proxying the response object is very difficult.
    if hasattr(return_val, "with_cleanup_hook"):
        try:
            return_val.with_cleanup_hook(
                _Agent_run_streaming_cleanup_hook(
                    stream=return_val,
                    ft=ft,
                    linking_metadata=linking_metadata,
                    agent_name=agent_name,
                    agent_id=agent_id,
                )
            )
            return return_val
        except Exception:
            ft.__exit__(*sys.exc_info())
            return return_val

    # Non-streaming run() returns an awaitable. Return a coroutine that awaits it and records the
    # LlmAgent event on completion.
    return _wrap_Agent_run_coroutine(return_val, ft, linking_metadata, agent_name, agent_id)


async def _wrap_Agent_run_coroutine(coro, ft, linking_metadata, agent_name, agent_id):
    # Wrap the corountine returned by Agent.run() and record events when it completes.
    try:
        return_val = await coro
    except Exception:
        transaction = current_transaction()
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

    transaction = current_transaction()
    ft.__exit__(None, None, None)
    _record_agent_event(
        transaction=transaction, ft=ft, linking_metadata=linking_metadata, agent_name=agent_name, agent_id=agent_id
    )
    return return_val


def _Agent_run_streaming_cleanup_hook(*, stream, ft, linking_metadata, agent_name, agent_id):
    def _nr_streaming_cleanup_hook():
        transaction = current_transaction()
        if not transaction:
            return

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


# ===================
# Context Propagation
# ===================


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


def instrument_agent_framwork__agents(module):
    if hasattr(module, "Agent"):
        if hasattr(module.Agent, "run"):
            wrap_function_wrapper(module, "Agent.run", wrap_Agent_run)


def instrument_agent_framwork_bedrock__chat_client(module):
    if hasattr(module, "BedrockChatClient"):
        if hasattr(module.BedrockChatClient, "_invoke_converse"):
            wrap_function_wrapper(module, "BedrockChatClient._invoke_converse", wrap_BedrockChatClient__invoke_converse)

        if hasattr(module.BedrockChatClient, "_prepare_options"):
            wrap_function_wrapper(module, "BedrockChatClient._prepare_options", wrap_BedrockChatClient__prepare_options)
