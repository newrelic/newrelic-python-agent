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
import traceback
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

GEMINI_VERSION = get_package_version("google-genai")
EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE = "Exception occurred in Gemini instrumentation: While reporting an exception in Gemini, another exception occurred. Report this issue to New Relic Support.\n%s"
RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Gemini instrumentation: Failed to record LLM events. Please report this issue to New Relic Support.\n%s"

_logger = logging.getLogger(__name__)


def wrap_embed_content_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Gemini", GEMINI_VERSION)
    transaction._add_agent_attribute("llm", True)

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/embedding/Gemini")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        response = wrapped(*args, **kwargs)
    except Exception as exc:
        _record_embedding_error(transaction, embedding_id, linking_metadata, kwargs, ft, exc)
        raise
    ft.__exit__(None, None, None)

    if not response:
        return response

    _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft)
    return response


async def wrap_embed_content_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Gemini", GEMINI_VERSION)
    transaction._add_agent_attribute("llm", True)

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/embedding/Gemini")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        response = await wrapped(*args, **kwargs)
    except Exception as exc:
        _record_embedding_error(transaction, embedding_id, linking_metadata, kwargs, ft, exc)
        raise
    ft.__exit__(None, None, None)

    if not response:
        return response

    _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft)
    return response


def _record_embedding_error(transaction, embedding_id, linking_metadata, kwargs, ft, exc):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")

    notice_error_attributes = {}
    try:
        embedding_content = kwargs.get("contents")
        embedding_content = str(embedding_content) if embedding_content else ""
        model = kwargs.get("model")

        notice_error_attributes = {
            "http.statusCode": getattr(exc, "code", None),
            "error.message": getattr(exc, "message", None),
            "error.code": getattr(exc, "status", None),  # ex: 'NOT_FOUND'
            "embedding_id": embedding_id,
        }
    except Exception:
        _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

    message = notice_error_attributes.pop("error.message", None)
    if message:
        exc._nr_message = message

    ft.notice_error(attributes=notice_error_attributes)
    # Exit the trace now so that the duration is calculated.
    ft.__exit__(*sys.exc_info())

    try:
        error_embedding_dict = {
            "id": embedding_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "token_count": (
                settings.ai_monitoring.llm_token_count_callback(model, embedding_content)
                if settings.ai_monitoring.llm_token_count_callback
                else None
            ),
            "request.model": model,
            "vendor": "gemini",
            "ingest_source": "Python",
            "duration": ft.duration * 1000,
            "error": True,
        }
        if settings.ai_monitoring.record_content.enabled:
            error_embedding_dict["contents"] = embedding_content

        error_embedding_dict.update(_get_llm_attributes(transaction))
        transaction.record_custom_event("LlmEmbedding", error_embedding_dict)
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


def _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    try:
        embedding_content = kwargs.get("contents")
        embedding_content = str(embedding_content) if embedding_content else ""
        request_model = kwargs.get("model")

        full_embedding_response_dict = {
            "id": embedding_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "token_count": (
                settings.ai_monitoring.llm_token_count_callback(request_model, embedding_content)
                if settings.ai_monitoring.llm_token_count_callback
                else None
            ),
            "request.model": request_model,
            "duration": ft.duration * 1000,
            "vendor": "gemini",
            "ingest_source": "Python",
        }
        if settings.ai_monitoring.record_content.enabled:
            full_embedding_response_dict["contents"] = embedding_content

        full_embedding_response_dict.update(_get_llm_attributes(transaction))

        transaction.record_custom_event("LlmEmbedding", full_embedding_response_dict)

    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


def _get_llm_attributes(transaction):
    """Returns llm.* custom attributes off of the transaction."""
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def instrument_genai_models(module):
    if hasattr(module, "Models"):
        wrap_function_wrapper(module, "Models.embed_content", wrap_embed_content_sync)

    if hasattr(module, "AsyncModels"):
        wrap_function_wrapper(module, "AsyncModels.embed_content", wrap_embed_content_async)
