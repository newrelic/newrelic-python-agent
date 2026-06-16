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
from newrelic.common.llm_utils import AsyncLLMStreamProxy, _get_llm_metadata
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)
GOOGLEADK_VERSION = get_package_version("google-adk")

RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Google ADK instrumentation: Failed to record LLM events. Please report this issue to New Relic Support."
AGENT_EVENT_FAILURE_LOG_MESSAGE = "Exception occurred in Google ADK instrumentation: Failed to record agent data. Please report this issue to New Relic Support."


def wrap_llm_agent__run_async_impl(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("GoogleADK", GOOGLEADK_VERSION)
    transaction._add_agent_attribute("llm", True)

    func_name = callable_name(wrapped)
    agent_name = getattr(instance, "name", "agent")
    function_trace_name = f"{func_name}/{agent_name}"
    agentic_subcomponent_data = {"type": "APM-AI_AGENT", "name": agent_name}

    ft = FunctionTrace(name=function_trace_name, group="Llm/agent/GoogleADK")
    ft.__enter__()
    ft._add_agent_attribute("subcomponent", json.dumps(agentic_subcomponent_data))

    linking_metadata = get_trace_linking_metadata()
    agent_id = str(uuid.uuid4())

    try:
        return_val = wrapped(*args, **kwargs)
    except Exception:
        ft.__exit__(*sys.exc_info())
        raise

    try:
        proxied_return_val = AsyncLLMStreamProxy(
            wrapped=return_val,
            on_stop_iteration=_record_agent_event_on_stop_iteration,
            on_error=_handle_agent_streaming_completion_error,
        )
        proxied_return_val._nr_ft = ft
        proxied_return_val._nr_metadata = linking_metadata
        proxied_return_val._nr_adk_attrs = {"agent_name": agent_name, "agent_id": agent_id}
        return proxied_return_val
    except Exception:
        ft.__exit__(*sys.exc_info())
        return return_val


def _record_agent_event_on_stop_iteration(self, transaction):
    if hasattr(self, "_nr_ft"):
        linking_metadata = self._nr_metadata or get_trace_linking_metadata()
        self._nr_ft.__exit__(None, None, None)
        try:
            adk_attrs = getattr(self, "_nr_adk_attrs", {})
            if not adk_attrs:
                return

            agent_name = adk_attrs.get("agent_name", "agent")
            agent_id = adk_attrs.get("agent_id")
            agent_event_dict = _construct_base_agent_event_dict(
                agent_name=agent_name, agent_id=agent_id, transaction=transaction, linking_metadata=linking_metadata
            )
            agent_event_dict["duration"] = self._nr_ft.duration * 1000
            transaction.record_custom_event("LlmAgent", agent_event_dict)
        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            if hasattr(self, "_nr_adk_attrs"):
                self._nr_adk_attrs.clear()


def _handle_agent_streaming_completion_error(self, transaction):
    if hasattr(self, "_nr_ft"):
        adk_attrs = getattr(self, "_nr_adk_attrs", {})
        if not adk_attrs:
            self._nr_ft.__exit__(*sys.exc_info())
            return

        linking_metadata = self._nr_metadata or get_trace_linking_metadata()

        try:
            agent_name = adk_attrs.get("agent_name", "agent")
            agent_id = adk_attrs.get("agent_id")

            self._nr_ft.notice_error(attributes={"agent_id": agent_id})
            self._nr_ft.__exit__(*sys.exc_info())

            agent_event_dict = _construct_base_agent_event_dict(
                agent_name=agent_name, agent_id=agent_id, transaction=transaction, linking_metadata=linking_metadata
            )
            agent_event_dict.update({"duration": self._nr_ft.duration * 1000, "error": True})
            transaction.record_custom_event("LlmAgent", agent_event_dict)
        except Exception:
            _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            if hasattr(self, "_nr_adk_attrs"):
                self._nr_adk_attrs.clear()


def _construct_base_agent_event_dict(agent_name, agent_id, transaction, linking_metadata):
    try:
        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": "google_adk",
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        _logger.warning(AGENT_EVENT_FAILURE_LOG_MESSAGE, exc_info=True)
        agent_event_dict = {}

    return agent_event_dict


def instrument_googleadk_agents_llm_agent(module):
    if hasattr(module, "LlmAgent") and hasattr(module.LlmAgent, "_run_async_impl"):
        wrap_function_wrapper(module, "LlmAgent._run_async_impl", wrap_llm_agent__run_async_impl)
