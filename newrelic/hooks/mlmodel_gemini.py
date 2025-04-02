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
import traceback
import uuid
import time
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

GEMINI_VERSION = get_package_version("google-genai")
EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE = "Exception occurred in Gemini instrumentation: While reporting an exception in Gemini, another exception occurred. Report this issue to New Relic Support.\n%s"
RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in Gemini instrumentation: Failed to record LLM events. Please report this issue to New Relic Support.\n%s"
STREAM_PARSING_FAILURE_LOG_MESSAGE = "Exception occurred in Gemini instrumentation: Failed to process event stream information. Please report this issue to New Relic Support.\n%s"

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

    _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft, response)
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

    _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft, response)
    return response


def _record_embedding_error(transaction, embedding_id, linking_metadata, kwargs, ft, exc):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    model = kwargs.get("model")

    notice_error_attributes = {}
    try:
        embedding_content = kwargs.get("contents")
        embedding_content = str(embedding_content) if embedding_content else None

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


def _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft, response):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    try:
        embedding_content = kwargs.get("contents")
        embedding_content = str(embedding_content) if embedding_content else None
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


def wrap_generate_content_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Gemini", GEMINI_VERSION)
    transaction._add_agent_attribute("llm", True)

    completion_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/completion/Gemini")
    ft.__enter__()

    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = wrapped(*args, **kwargs)
    except Exception as exc:
        _record_generation_error(transaction, linking_metadata, completion_id, kwargs, ft, exc)
        raise

    ft.__exit__(None, None, None)

    _handle_generation_success(transaction, linking_metadata, completion_id, kwargs, ft, return_val)

    return return_val


async def wrap_generate_content_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Gemini", GEMINI_VERSION)
    transaction._add_agent_attribute("llm", True)

    completion_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/completion/Gemini")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception as exc:
        _record_generation_error(transaction, linking_metadata, completion_id, kwargs, ft, exc)
        raise

    _handle_generation_success(transaction, linking_metadata, completion_id, kwargs, ft, return_val)
    ft.__exit__(None, None, None)

    return return_val


def _get_llm_attributes(transaction):
    """Returns llm.* custom attributes off of the transaction."""
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def _record_generation_error(transaction, linking_metadata, completion_id, kwargs, ft, exc):
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    notice_error_attributes = {}
    messages = kwargs.get("contents")  # kwargs.get("contents")[1].parts[0].text - loop through contents
    if messages:
        last_request_message_index = len(messages) - 1
        request_message_dict = messages[last_request_message_index]
        if hasattr(request_message_dict, "to_json_dict"):
            request_message_dict = messages[last_request_message_index].to_json_dict()
    else:
        request_message_dict = {}

    generation_config = kwargs.get("config")
    if generation_config:
        generation_config_dict = generation_config.model_dump()
        request_temperature = generation_config_dict.get("temperature")
        request_max_tokens = generation_config_dict.get("max_output_tokens")
    else:
        request_temperature = None
        request_max_tokens = None

    try:
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "code", None),
            "error.message": getattr(exc, "message", None),
            "error.code": getattr(exc, "status", None),  # ex: 'NOT_FOUND'
            "completion_id": completion_id,
        }
    except Exception:
        _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))
    # Override the default message if it is not empty.
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
            "response.number_of_messages": len(messages),
            "request.model": request_model,
            "request.temperature": request_temperature,
            "request.max_tokens": request_max_tokens,
            "vendor": "gemini",
            "ingest_source": "Python",
            "duration": ft.duration * 1000,
            "error": True,
        }
        llm_metadata = _get_llm_attributes(transaction)
        error_chat_completion_dict.update(llm_metadata)
        transaction.record_custom_event("LlmChatCompletionSummary", error_chat_completion_dict)

        output_message_list = []

        create_chat_completion_message_event(
            transaction,
            request_message_dict,
            completion_id,
            span_id,
            trace_id,
            request_model,  # Passing the request model as the response model here since we do not have access to a response model
            request_model,
            llm_metadata,
            output_message_list,
        )
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


def _handle_generation_success(transaction, linking_metadata, completion_id, kwargs, ft, return_val):
    if not return_val:
        # ft.__exit__(None, None, None)
        return

    try:
        response = return_val
        # Response objects are pydantic models so this function call converts the response into a dict
        if hasattr(response, "model_dump"):
            response = response.model_dump()
        _record_generation_success(transaction, linking_metadata, completion_id, kwargs, ft, response)
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


def _record_generation_success(transaction, linking_metadata, completion_id, kwargs, ft, response):
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    try:
        if response:
            response_model = response.get("model_version")
            finish_reason = response.get("candidates")[0].get("finish_reason").value
            output_message_list = [
                response.get("candidates")[0].get("content")
            ]  # .get("parts")[0].get("text")]   response.get("candidates")[0].get("content")][0].get("role")
        else:
            response_model = None
            output_message_list = []
            finish_reason = None

        request_model = kwargs.get("model")
        messages = kwargs.get("contents")  # kwargs.get("contents")[1].parts[0].text - loop through contents

        last_request_message_index = len(messages) - 1
        input_message_dict = messages[last_request_message_index]
        if hasattr(input_message_dict, "to_json_dict"):
            input_message_dict = messages[last_request_message_index].to_json_dict()

        generation_config = kwargs.get("config")

        if generation_config:
            generation_config_dict = generation_config.model_dump()
            request_temperature = generation_config_dict.get("temperature")
            request_max_tokens = generation_config_dict.get("max_output_tokens")
        else:
            request_temperature = None
            request_max_tokens = None

        full_chat_completion_summary_dict = {
            "id": completion_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "request.model": request_model,
            "request.temperature": request_temperature,
            "request.max_tokens": request_max_tokens,
            "vendor": "gemini",
            "ingest_source": "Python",
            "duration": ft.duration * 1000,
            "response.model": response_model,
            "response.choices.finish_reason": finish_reason,
            "response.number_of_messages": 1 + len(output_message_list),
        }

        llm_metadata = _get_llm_attributes(transaction)
        full_chat_completion_summary_dict.update(llm_metadata)
        transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)

        create_chat_completion_message_event(
            transaction,
            input_message_dict,
            completion_id,
            span_id,
            trace_id,
            response_model,
            request_model,
            llm_metadata,
            output_message_list,
        )
    except Exception:
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


def create_chat_completion_message_event(
    transaction,
    input_messages,
    chat_completion_id,
    span_id,
    trace_id,
    response_model,
    request_model,
    llm_metadata,
    output_message_list,
):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    if isinstance(input_messages, str):
        input_message_content = input_messages
        input_role = "user"
    elif isinstance(input_messages, dict):
        input_message_content = input_messages.get("parts")[0].get("text")
        input_role = input_messages.get("role")
    else:
        input_message_content = ""
        input_role = "user"

    message_id = str(uuid.uuid4())

    chat_completion_input_message_dict = {
        "id": message_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "token_count": (
            settings.ai_monitoring.llm_token_count_callback(request_model, input_message_content)
            if settings.ai_monitoring.llm_token_count_callback
            else None
        ),
        "role": input_role,
        "completion_id": chat_completion_id,
        "sequence": 0,
        "response.model": response_model,
        "vendor": "gemini",
        "ingest_source": "Python",
    }

    if settings.ai_monitoring.record_content.enabled:
        chat_completion_input_message_dict["content"] = input_message_content

    chat_completion_input_message_dict.update(llm_metadata)

    transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_input_message_dict)

    if output_message_list:
        # Loop through all output messages received from the LLM response and emit a custom event for each one
        for index, message in enumerate(output_message_list):
            message_content = message.get("parts")[0].get("text")

            # Add offset of input_message_length so we don't receive any duplicate index values that match the input message IDs
            index += 1

            message_id = str(uuid.uuid4())

            chat_completion_output_message_dict = {
                "id": message_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "token_count": (
                    settings.ai_monitoring.llm_token_count_callback(response_model, message_content)
                    if settings.ai_monitoring.llm_token_count_callback
                    else None
                ),
                "role": message.get("role"),
                "completion_id": chat_completion_id,
                "sequence": index,
                "response.model": response_model,
                "vendor": "gemini",
                "ingest_source": "Python",
                "is_response": True,
            }

            if settings.ai_monitoring.record_content.enabled:
                chat_completion_output_message_dict["content"] = message_content

            chat_completion_output_message_dict.update(llm_metadata)

            transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_output_message_dict)


def instrument_genai_models(module):
    if hasattr(module, "Models"):
        wrap_function_wrapper(module, "Models.generate_content", wrap_generate_content_sync)
        wrap_function_wrapper(module, "Models.embed_content", wrap_embed_content_sync)

    if hasattr(module, "AsyncModels"):
        wrap_function_wrapper(module, "AsyncModels.generate_content", wrap_generate_content_async)
        wrap_function_wrapper(module, "AsyncModels.embed_content", wrap_embed_content_async)
