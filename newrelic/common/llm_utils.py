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

_logger = logging.getLogger(__name__)
RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Autogen instrumentation: Failed to record LLM events. Please report this issue to New Relic Support.\n%s"


def _get_llm_metadata(transaction):
    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}
    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def _construct_base_agent_event_dict(agent_name, agent_id, transaction, linking_metadata, vendor_name):
    try:
        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": vendor_name,
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        agent_event_dict = {}

    return agent_event_dict
