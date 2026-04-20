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
import time
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

ANTHROPIC_VERSION = get_package_version("anthropic")
RECORD_EVENTS_FAILURE_LOG_MESSAGE = (
    "Exception occurred in Anthropic instrumentation: Failed to record LLM events. "
    "Please report this issue to New Relic Support.\n "
)

_logger = logging.getLogger(__name__)


def _get_llm_attributes(transaction):
    """Returns llm.* custom attributes off of the transaction."""
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def _extract_message_content(content):
    """Extract text content from an Anthropic message content field.

    Content can be a string or a list of content block dicts/objects.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            else:
                if getattr(block, "type", None) == "text":
                    parts.append(getattr(block, "text", ""))
        return " ".join(parts) if parts else None
    return None


def _extract_exception_message(exc):
    """Attempt to extract just the error message from the exception body, and fallback to dumping it all to a string."""
    try:
        error_body = exc.body
        if isinstance(error_body, list) and len(error_body) == 1:
            # Unpack single exceptions in lists if possible
            error_body = error_body[0]

        # Process the unpacked exception as a dict, or load from json
        if isinstance(error_body, dict):
            # Grab just the error message to report
            return error_body["error"]["message"]
        elif isinstance(error_body, str):
            error_body_dict = json.loads(error_body)
            return error_body_dict["error"]["message"]
        else:
            return str(error_body)
    except Exception:
        return str(exc)


def wrap_messages_create_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    if kwargs.get("stream"):
        # TODO: Streaming instrumentation not yet implemented.
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Anthropic", ANTHROPIC_VERSION)
    transaction._add_agent_attribute("llm", True)

    completion_id = str(uuid.uuid4())
    request_timestamp = int(1000.0 * time.time())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/completion/Anthropic")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = wrapped(*args, **kwargs)
    except Exception as exc:
        _record_completion_error(
            transaction=transaction,
            linking_metadata=linking_metadata,
            completion_id=completion_id,
            kwargs=kwargs,
            ft=ft,
            exc=exc,
            request_timestamp=request_timestamp,
        )
        raise

    # Non-streaming path
    ft.__exit__(None, None, None)

    response = return_val
    usage = getattr(response, "usage", None)
    _record_completion_success(
        transaction=transaction,
        linking_metadata=linking_metadata,
        completion_id=completion_id,
        kwargs=kwargs,
        ft=ft,
        response_id=getattr(response, "id", None),
        response_model=getattr(response, "model", None),
        stop_reason=getattr(response, "stop_reason", None),
        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        response_content=getattr(response, "content", None),
        request_timestamp=request_timestamp,
    )
    return return_val


async def wrap_messages_create_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    if kwargs.get("stream"):
        # TODO: Streaming instrumentation not yet implemented.
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Anthropic", ANTHROPIC_VERSION)
    transaction._add_agent_attribute("llm", True)

    completion_id = str(uuid.uuid4())
    request_timestamp = int(1000.0 * time.time())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/completion/Anthropic")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception as exc:
        _record_completion_error(
            transaction=transaction,
            linking_metadata=linking_metadata,
            completion_id=completion_id,
            kwargs=kwargs,
            ft=ft,
            exc=exc,
            request_timestamp=request_timestamp,
        )
        raise

    # Non-streaming path
    ft.__exit__(None, None, None)

    response = return_val
    usage = getattr(response, "usage", None)
    _record_completion_success(
        transaction=transaction,
        linking_metadata=linking_metadata,
        completion_id=completion_id,
        kwargs=kwargs,
        ft=ft,
        response_id=getattr(response, "id", None),
        response_model=getattr(response, "model", None),
        stop_reason=getattr(response, "stop_reason", None),
        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        response_content=getattr(response, "content", None),
        request_timestamp=request_timestamp,
    )
    return return_val


def _record_completion_error(*, transaction, linking_metadata, completion_id, kwargs, ft, exc, request_timestamp=None):
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    request_temperature = kwargs.get("temperature")
    request_max_tokens = kwargs.get("max_tokens")

    messages = kwargs.get("messages", [])

    error_message = _extract_exception_message(exc)

    notice_error_attributes = {
        "http.statusCode": getattr(exc, "status_code", None),
        "error.message": error_message,
        "error.code": type(exc).__name__,
        "completion_id": completion_id,
    }

    message = notice_error_attributes.pop("error.message", None)
    if message:
        exc._nr_message = message

    ft.notice_error(attributes=notice_error_attributes)
    # Stop the span now so we compute the duration before we create the events.
    ft.__exit__(*sys.exc_info())

    try:
        request_model = kwargs.get("model")

        error_chat_completion_dict = {
            "id": completion_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "request.model": request_model,
            "request.temperature": request_temperature,
            "request.max_tokens": request_max_tokens,
            "vendor": "anthropic",
            "ingest_source": "Python",
            "duration": ft.duration * 1000,
            "error": True,
            "timestamp": request_timestamp,
            "response.number_of_messages": len(messages),
        }

        llm_metadata = _get_llm_attributes(transaction)
        error_chat_completion_dict.update(llm_metadata)
        transaction.record_custom_event("LlmChatCompletionSummary", error_chat_completion_dict)

        # Record input messages even on error
        create_chat_completion_message_event(
            transaction=transaction,
            messages=messages,
            completion_id=completion_id,
            span_id=span_id,
            trace_id=trace_id,
            response_id=None,
            response_model=request_model,
            request_model=request_model,
            llm_metadata=llm_metadata,
            response_content=None,
            request_timestamp=request_timestamp,
        )
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)


def _record_completion_success(
    *,
    transaction,
    linking_metadata,
    completion_id,
    kwargs,
    ft,
    response_id,
    response_model,
    stop_reason,
    input_tokens,
    output_tokens,
    response_content,
    request_timestamp=None,
    time_to_first_token=None,
):
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    try:
        messages = kwargs.get("messages", [])
        request_model = kwargs.get("model")
        request_temperature = kwargs.get("temperature")
        request_max_tokens = kwargs.get("max_tokens")

        # total_tokens = (
        #     (input_tokens + output_tokens) if (input_tokens is not None and output_tokens is not None) else None
        # )
        number_of_messages = len(messages) + (1 if response_content else 0)

        full_chat_completion_summary_dict = {
            "id": completion_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "request.model": request_model,
            "request.temperature": request_temperature,
            "request.max_tokens": request_max_tokens,
            "vendor": "anthropic",
            "ingest_source": "Python",
            "duration": ft.duration * 1000,
            "response.model": response_model,
            "response.choices.finish_reason": stop_reason,
            "response.number_of_messages": number_of_messages,
            # "response.usage.total_tokens": total_tokens,
            # "response.usage.prompt_tokens": input_tokens,
            # "response.usage.completion_tokens": output_tokens,
            "timestamp": request_timestamp,
            "time_to_first_token": time_to_first_token,
        }

        llm_metadata = _get_llm_attributes(transaction)
        full_chat_completion_summary_dict.update(llm_metadata)
        transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)

        create_chat_completion_message_event(
            transaction=transaction,
            messages=messages,
            completion_id=completion_id,
            span_id=span_id,
            trace_id=trace_id,
            response_id=response_id,
            response_model=response_model,
            request_model=request_model,
            llm_metadata=llm_metadata,
            response_content=response_content,
            request_timestamp=request_timestamp,
        )
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)


def create_chat_completion_message_event(
    *,
    transaction,
    messages,
    completion_id,
    span_id,
    trace_id,
    response_id,
    response_model,
    request_model,
    llm_metadata,
    response_content,
    request_timestamp=None,
):
    try:
        settings = transaction.settings or global_settings()

        # Record one event per input message
        for sequence, message in enumerate(messages):
            role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
            content_field = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
            message_content = _extract_message_content(content_field)

            message_id = str(uuid.uuid4())
            input_message_dict = {
                "id": message_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "token_count": (
                    settings.ai_monitoring.llm_token_count_callback(request_model, message_content)
                    if settings.ai_monitoring.llm_token_count_callback and message_content
                    else None
                ),
                "role": role,
                "completion_id": completion_id,
                "sequence": sequence,
                "response.model": response_model,
                "vendor": "anthropic",
                "ingest_source": "Python",
            }
            if settings.ai_monitoring.record_content.enabled and message_content is not None:
                input_message_dict["content"] = message_content
            if request_timestamp:
                input_message_dict["timestamp"] = request_timestamp

            input_message_dict.update(llm_metadata)
            transaction.record_custom_event("LlmChatCompletionMessage", input_message_dict)

        # Record one event for the response
        if response_content:
            response_sequence = len(messages)
            # response_content may be a plain string (streaming path) or a list of content blocks (non-streaming).
            if isinstance(response_content, str):
                response_text = response_content
            else:
                response_text = " ".join(
                    block.text for block in response_content if getattr(block, "type", None) == "text"
                )

            response_message_id = f"{response_id}-{response_sequence}" if response_id else str(uuid.uuid4())
            output_message_dict = {
                "id": response_message_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "token_count": (
                    settings.ai_monitoring.llm_token_count_callback(response_model, response_text)
                    if settings.ai_monitoring.llm_token_count_callback and response_text
                    else None
                ),
                "role": "assistant",
                "completion_id": completion_id,
                "sequence": response_sequence,
                "response.model": response_model,
                "vendor": "anthropic",
                "ingest_source": "Python",
                "is_response": True,
            }
            if settings.ai_monitoring.record_content.enabled and response_text:
                output_message_dict["content"] = response_text

            output_message_dict.update(llm_metadata)
            transaction.record_custom_event("LlmChatCompletionMessage", output_message_dict)
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)


def instrument_anthropic_messages(module):
    if hasattr(module, "Messages"):
        wrap_function_wrapper(module, "Messages.create", wrap_messages_create_sync)

    if hasattr(module, "AsyncMessages"):
        wrap_function_wrapper(module, "AsyncMessages.create", wrap_messages_create_async)
