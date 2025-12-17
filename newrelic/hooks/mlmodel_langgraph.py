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

from newrelic.api.function_trace import FunctionTrace

from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.llm_utils import _get_llm_metadata
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

LANGGRAPH_VERSION = get_package_version("langgraph")
RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in LangGraph instrumentation: Failed to record LLM events. Please report this issue to New Relic Support.\n%s"


def wrap_invoke(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangGraph", LANGGRAPH_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(transaction, "_nr_agent_name", "agent")
    agent_id = str(uuid.uuid4())
    agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangGraph")
    ft.__enter__()

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        # If we hit an exception, append the error attribute and duration from the exited function trace
        agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmAgent", agent_event_dict)
        raise

    ft.__exit__(None, None, None)
    agent_event_dict.update({"duration": ft.duration * 1000})

    transaction.record_custom_event("LlmAgent", agent_event_dict)

    return return_val

async def wrap_ainvoke(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangGraph", LANGGRAPH_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(transaction, "_nr_agent_name", "agent")
    agent_id = str(uuid.uuid4())
    agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangGraph")
    ft.__enter__()

    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        # If we hit an exception, append the error attribute and duration from the exited function trace
        agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmAgent", agent_event_dict)
        raise

    ft.__exit__(None, None, None)
    agent_event_dict.update({"duration": ft.duration * 1000})

    transaction.record_custom_event("LlmAgent", agent_event_dict)

    return return_val

def wrap_stream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangGraph", LANGGRAPH_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(transaction, "_nr_agent_name", "agent")
    agent_id = str(uuid.uuid4())
    agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangGraph")
    ft.__enter__()

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        # If we hit an exception, append the error attribute and duration from the exited function trace
        agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmAgent", agent_event_dict)
        raise

    ft.__exit__(None, None, None)
    agent_event_dict.update({"duration": ft.duration * 1000})

    transaction.record_custom_event("LlmAgent", agent_event_dict)

    return return_val

async def wrap_astream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangGraph", LANGGRAPH_VERSION)
    transaction._add_agent_attribute("llm", True)

    agent_name = getattr(transaction, "_nr_agent_name", "agent")
    agent_id = str(uuid.uuid4())
    agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
    func_name = callable_name(wrapped)
    function_trace_name = f"{func_name}/{agent_name}"

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangGraph")
    ft.__enter__()

    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"agent_id": agent_id})
        ft.__exit__(*sys.exc_info())
        # If we hit an exception, append the error attribute and duration from the exited function trace
        agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
        transaction.record_custom_event("LlmAgent", agent_event_dict)
        raise

    ft.__exit__(None, None, None)
    agent_event_dict.update({"duration": ft.duration * 1000})

    transaction.record_custom_event("LlmAgent", agent_event_dict)

    return return_val

def _construct_base_agent_event_dict(agent_name, agent_id, transaction):
    try:
        linking_metadata = get_trace_linking_metadata()

        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": "langgraph",
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        agent_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return agent_event_dict

def instrument_langgraph__internal__runnable(module):
    if hasattr(module, "RunnableSeq"):
        wrap_function_wrapper(module, "RunnableSeq.invoke", wrap_invoke)
        wrap_function_wrapper(module, "RunnableSeq.ainvoke", wrap_ainvoke)
        wrap_function_wrapper(module, "RunnableSeq.stream", wrap_stream)
        wrap_function_wrapper(module, "RunnableSeq.astream", wrap_astream)