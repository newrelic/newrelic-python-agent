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

import uuid

import openai

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

OPENAI_VERSION = get_package_version("openai")
OPENAI_VERSION_TUPLE = tuple(map(int, OPENAI_VERSION.split(".")))
OPENAI_V1 = OPENAI_VERSION_TUPLE >= (1,)


def wrap_embedding_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction or kwargs.get("stream", False):
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", "") if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

    settings = transaction.settings if transaction.settings is not None else global_settings()

    function_name = wrapped.__name__

    with FunctionTrace(name=function_name, group="Llm/embedding/OpenAI") as ft:
        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id", "")
        trace_id = available_metadata.get("trace.id", "")

        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            if OPENAI_V1:
                response = getattr(exc, "response", "")
                response_headers = getattr(response, "headers", "")
                exc_organization = response_headers.get("openai-organization", "") if response_headers else ""
                # There appears to be a bug here in openai v1 where despite having code,
                # param, etc in the error response, they are not populated on the exception
                # object so grab them from the response body object instead.
                body = getattr(exc, "body", {}) or {}
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "status_code", "") or "",
                    "error.message": body.get("message", "") or "",
                    "error.code": body.get("code", "") or "",
                    "error.param": body.get("param", "") or "",
                    "embedding_id": embedding_id,
                }
            else:
                exc_organization = getattr(exc, "organization", "")
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "http_status", ""),
                    "error.message": getattr(exc, "_message", ""),
                    "error.code": getattr(getattr(exc, "error", ""), "code", ""),
                    "error.param": getattr(exc, "param", ""),
                    "embedding_id": embedding_id,
                }
            message = notice_error_attributes.pop("error.message")
            if message:
                exc._nr_message = message
            ft.notice_error(
                attributes=notice_error_attributes,
            )

            error_embedding_dict = {
                "id": embedding_id,
                "appName": settings.app_name,
                "api_key_last_four_digits": api_key_last_four_digits,
                "span_id": span_id,
                "trace_id": trace_id,
                "transaction_id": transaction.guid,
                "input": kwargs.get("input", ""),
                "request.model": kwargs.get("model") or kwargs.get("engine") or "",
                "vendor": "openAI",
                "ingest_source": "Python",
                "response.organization": "" if exc_organization is None else exc_organization,
                "duration": ft.duration,
                "error": True,
            }

            transaction.record_custom_event("LlmEmbedding", error_embedding_dict)

            raise

    if not response:
        return response

    response_headers = getattr(response, "_nr_response_headers", None)

    # In v1, response objects are pydantic models so this function call converts the object back to a dictionary for backwards compatibility
    # Use standard response object returned from create call for v0
    if OPENAI_V1:
        attribute_response = response.model_dump()
    else:
        attribute_response = response

    request_id = response_headers.get("x-request-id", "") if response_headers else ""

    response_model = attribute_response.get("model", "") or ""
    response_usage = attribute_response.get("usage", {}) or {}
    api_type = getattr(attribute_response, "api_type", "")
    organization = response_headers.get("openai-organization", "") if OPENAI_V1 else attribute_response.organization

    full_embedding_response_dict = {
        "id": embedding_id,
        "appName": settings.app_name,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "input": kwargs.get("input", ""),
        "api_key_last_four_digits": f"sk-{api_key[-4:]}" if api_key else "",
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "request_id": request_id,
        "duration": ft.duration,
        "response.model": response_model,
        "response.organization": organization,
        "response.api_type": api_type,  # API type was removed in v1
        "response.usage.total_tokens": response_usage.get("total_tokens", "") if response_usage else "",
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens", "") if response_usage else "",
        "response.headers.llmVersion": response_headers.get("openai-version", ""),
        "response.headers.ratelimitLimitRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-requests", True
        ),
        "response.headers.ratelimitLimitTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-tokens", True
        ),
        "response.headers.ratelimitResetTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-tokens", False
        ),
        "response.headers.ratelimitResetRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-requests", False
        ),
        "response.headers.ratelimitRemainingTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-tokens", True
        ),
        "response.headers.ratelimitRemainingRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-requests", True
        ),
        "vendor": "openAI",
        "ingest_source": "Python",
    }

    transaction.record_custom_event("LlmEmbedding", full_embedding_response_dict)

    return response


def wrap_chat_completion_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction or kwargs.get("stream", False):
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    request_message_list = kwargs.get("messages", [])

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", None) if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

    # Get conversation ID off of the transaction
    custom_attrs_dict = transaction._custom_params
    conversation_id = custom_attrs_dict.get("llm.conversation_id", "")

    settings = transaction.settings if transaction.settings is not None else global_settings()
    app_name = settings.app_name
    completion_id = str(uuid.uuid4())

    function_name = wrapped.__name__

    with FunctionTrace(name=function_name, group="Llm/completion/OpenAI") as ft:
        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id", "")
        trace_id = available_metadata.get("trace.id", "")

        try:
            return_val = wrapped(*args, **kwargs)
        except Exception as exc:
            if OPENAI_V1:
                response = getattr(exc, "response", "")
                response_headers = getattr(response, "headers", "")
                exc_organization = response_headers.get("openai-organization", "") if response_headers else ""
                # There appears to be a bug here in openai v1 where despite having code,
                # param, etc in the error response, they are not populated on the exception
                # object so grab them from the response body object instead.
                body = getattr(exc, "body", {}) or {}
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "status_code", "") or "",
                    "error.message": body.get("message", "") or "",
                    "error.code": body.get("code", "") or "",
                    "error.param": body.get("param", "") or "",
                    "completion_id": completion_id,
                }
            else:
                exc_organization = getattr(exc, "organization", "")
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "http_status", ""),
                    "error.message": getattr(exc, "_message", ""),
                    "error.code": getattr(getattr(exc, "error", ""), "code", ""),
                    "error.param": getattr(exc, "param", ""),
                    "completion_id": completion_id,
                }
            # Override the default message if it is not empty.
            message = notice_error_attributes.pop("error.message")
            if message:
                exc._nr_message = message

            ft.notice_error(
                attributes=notice_error_attributes,
            )
            # Gather attributes to add to embedding summary event in error context
            error_chat_completion_dict = {
                "id": completion_id,
                "appName": app_name,
                "conversation_id": conversation_id,
                "api_key_last_four_digits": api_key_last_four_digits,
                "span_id": span_id,
                "trace_id": trace_id,
                "transaction_id": transaction.guid,
                "response.number_of_messages": len(request_message_list),
                "request.model": kwargs.get("model") or kwargs.get("engine") or "",
                "request.temperature": kwargs.get("temperature", ""),
                "request.max_tokens": kwargs.get("max_tokens", ""),
                "vendor": "openAI",
                "ingest_source": "Python",
                "response.organization": "" if exc_organization is None else exc_organization,
                "duration": ft.duration,
                "error": True,
            }
            transaction.record_custom_event("LlmChatCompletionSummary", error_chat_completion_dict)

            create_chat_completion_message_event(
                transaction,
                app_name,
                request_message_list,
                completion_id,
                span_id,
                trace_id,
                "",
                None,
                "",
                conversation_id,
                None,
            )

            raise

    if not return_val:
        return return_val

    # At this point, we have a response so we can grab attributes only available on the response object
    response_headers = getattr(return_val, "_nr_response_headers", None)
    # In v1, response objects are pydantic models so this function call converts the
    # object back to a dictionary for backwards compatibility.
    response = return_val
    if OPENAI_V1:
        response = response.model_dump()

    response_model = response.get("model", "") or ""
    response_id = response.get("id")
    request_id = response_headers.get("x-request-id", "") if response_headers else ""

    response_usage = response.get("usage", {}) or {}

    messages = kwargs.get("messages", []) or []
    choices = response.get("choices", []) or []
    organization = (
        response_headers.get("openai-organization", "") if OPENAI_V1 else getattr(response, "organization", "")
    )

    full_chat_completion_summary_dict = {
        "id": completion_id,
        "appName": app_name,
        "conversation_id": conversation_id,
        "api_key_last_four_digits": api_key_last_four_digits,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "request.temperature": kwargs.get("temperature", ""),
        "request.max_tokens": kwargs.get("max_tokens", ""),
        "vendor": "openAI",
        "ingest_source": "Python",
        "request_id": request_id,
        "duration": ft.duration,
        "response.model": response_model,
        "response.organization": organization,
        "response.usage.completion_tokens": response_usage.get("completion_tokens", "") if response_usage else "",
        "response.usage.total_tokens": response_usage.get("total_tokens", "") if response_usage else "",
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens", "") if response_usage else "",
        "response.choices.finish_reason": choices[0].get("finish_reason", "") if choices else "",
        "response.api_type": getattr(response, "api_type", ""),
        "response.headers.llmVersion": response_headers.get("openai-version", ""),
        "response.headers.ratelimitLimitRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-requests", True
        ),
        "response.headers.ratelimitLimitTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-tokens", True
        ),
        "response.headers.ratelimitResetTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-tokens", False
        ),
        "response.headers.ratelimitResetRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-requests", False
        ),
        "response.headers.ratelimitRemainingTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-tokens", True
        ),
        "response.headers.ratelimitRemainingRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-requests", True
        ),
        "response.headers.ratelimitLimitTokensUsageBased": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-tokens_usage_based", True
        ),
        "response.headers.ratelimitResetTokensUsageBased": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-tokens_usage_based", False
        ),
        "response.headers.ratelimitRemainingTokensUsageBased": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-tokens_usage_based", True
        ),
        "response.number_of_messages": len(messages) + len(choices),
    }

    transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)

    input_message_list = list(messages)
    output_message_list = [choices[0].get("message", "")] if choices else None

    message_ids = create_chat_completion_message_event(
        transaction,
        settings.app_name,
        input_message_list,
        completion_id,
        span_id,
        trace_id,
        response_model,
        response_id,
        request_id,
        conversation_id,
        output_message_list,
    )

    # Cache message IDs on transaction for retrieval after OpenAI call completion.
    if not hasattr(transaction, "_nr_message_ids"):
        transaction._nr_message_ids = {}
    transaction._nr_message_ids[response_id] = message_ids

    return return_val


def check_rate_limit_header(response_headers, header_name, is_int):
    if not response_headers:
        return ""

    if header_name in response_headers:
        header_value = response_headers.get(header_name)
        if is_int:
            try:
                header_value = int(header_value)
            except Exception:
                pass
        return header_value
    else:
        return ""


def create_chat_completion_message_event(
    transaction,
    app_name,
    input_message_list,
    chat_completion_id,
    span_id,
    trace_id,
    response_model,
    response_id,
    request_id,
    conversation_id,
    output_message_list,
):
    message_ids = []

    # Loop through all input messages received from the create request and emit a custom event for each one
    for index, message in enumerate(input_message_list):
        message_content = message.get("content", "")

        # Response ID was set, append message index to it.
        if response_id:
            message_id = "%s-%d" % (response_id, index)
        # No response IDs, use random UUID
        else:
            message_id = str(uuid.uuid4())

        message_ids.append(message_id)

        chat_completion_input_message_dict = {
            "id": message_id,
            "appName": app_name,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction.guid,
            "content": message_content,
            "role": message.get("role", ""),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": response_model if response_model else "",
            "vendor": "openAI",
            "ingest_source": "Python",
        }

        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_input_message_dict)

    if output_message_list:
        # Loop through all output messages received from the LLM response and emit a custom event for each one
        for index, message in enumerate(output_message_list):
            message_content = message.get("content", "")

            # Add offset of input_message_length so we don't receive any duplicate index values that match the input message IDs
            index += len(input_message_list)

            # Response ID was set, append message index to it.
            if response_id:
                message_id = "%s-%d" % (response_id, index)
            # No response IDs, use random UUID
            else:
                message_id = str(uuid.uuid4())

            message_ids.append(message_id)

            chat_completion_output_message_dict = {
                "id": message_id,
                "appName": app_name,
                "conversation_id": conversation_id,
                "request_id": request_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "transaction_id": transaction.guid,
                "content": message_content,
                "role": message.get("role", ""),
                "completion_id": chat_completion_id,
                "sequence": index,
                "response.model": response_model if response_model else "",
                "vendor": "openAI",
                "ingest_source": "Python",
                "is_response": True,
            }

            transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_output_message_dict)

    return (conversation_id, request_id, message_ids)


async def wrap_embedding_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction or kwargs.get("stream", False):
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", "") if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

    settings = transaction.settings if transaction.settings is not None else global_settings()

    function_name = wrapped.__name__

    with FunctionTrace(name=function_name, group="Llm/embedding/OpenAI") as ft:
        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id", "")
        trace_id = available_metadata.get("trace.id", "")

        try:
            response = await wrapped(*args, **kwargs)
        except Exception as exc:
            if OPENAI_V1:
                response = getattr(exc, "response", "")
                response_headers = getattr(response, "headers", "")
                exc_organization = response_headers.get("openai-organization", "") if response_headers else ""
                # There appears to be a bug here in openai v1 where despite having code,
                # param, etc in the error response, they are not populated on the exception
                # object so grab them from the response body object instead.
                body = getattr(exc, "body", {}) or {}
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "status_code", "") or "",
                    "error.message": body.get("message", "") or "",
                    "error.code": body.get("code", "") or "",
                    "error.param": body.get("param", "") or "",
                    "embedding_id": embedding_id,
                }
            else:
                exc_organization = getattr(exc, "organization", "")
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "http_status", ""),
                    "error.message": getattr(exc, "_message", ""),
                    "error.code": getattr(getattr(exc, "error", ""), "code", ""),
                    "error.param": getattr(exc, "param", ""),
                    "embedding_id": embedding_id,
                }
            message = notice_error_attributes.pop("error.message")
            if message:
                exc._nr_message = message
            ft.notice_error(
                attributes=notice_error_attributes,
            )

            error_embedding_dict = {
                "id": embedding_id,
                "appName": settings.app_name,
                "api_key_last_four_digits": api_key_last_four_digits,
                "span_id": span_id,
                "trace_id": trace_id,
                "transaction_id": transaction.guid,
                "input": kwargs.get("input", ""),
                "request.model": kwargs.get("model") or kwargs.get("engine") or "",
                "vendor": "openAI",
                "ingest_source": "Python",
                "response.organization": "" if exc_organization is None else exc_organization,
                "duration": ft.duration,
                "error": True,
            }

            transaction.record_custom_event("LlmEmbedding", error_embedding_dict)

            raise

    if not response:
        return response

    response_headers = getattr(response, "_nr_response_headers", None)

    # In v1, response objects are pydantic models so this function call converts the object back to a dictionary for backwards compatibility
    # Use standard response object returned from create call for v0
    if OPENAI_V1:
        attribute_response = response.model_dump()
    else:
        attribute_response = response

    request_id = response_headers.get("x-request-id", "") if response_headers else ""

    response_model = attribute_response.get("model", "") or ""
    response_usage = attribute_response.get("usage", {}) or {}
    api_type = getattr(attribute_response, "api_type", "")
    organization = response_headers.get("openai-organization", "") if OPENAI_V1 else attribute_response.organization

    full_embedding_response_dict = {
        "id": embedding_id,
        "appName": settings.app_name,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "input": kwargs.get("input", ""),
        "api_key_last_four_digits": f"sk-{api_key[-4:]}" if api_key else "",
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "request_id": request_id,
        "duration": ft.duration,
        "response.model": response_model,
        "response.organization": organization,
        "response.api_type": api_type,  # API type was removed in v1
        "response.usage.total_tokens": response_usage.get("total_tokens", "") if response_usage else "",
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens", "") if response_usage else "",
        "response.headers.llmVersion": response_headers.get("openai-version", ""),
        "response.headers.ratelimitLimitRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-requests", True
        ),
        "response.headers.ratelimitLimitTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-tokens", True
        ),
        "response.headers.ratelimitResetTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-tokens", False
        ),
        "response.headers.ratelimitResetRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-requests", False
        ),
        "response.headers.ratelimitRemainingTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-tokens", True
        ),
        "response.headers.ratelimitRemainingRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-requests", True
        ),
        "vendor": "openAI",
        "ingest_source": "Python",
    }

    transaction.record_custom_event("LlmEmbedding", full_embedding_response_dict)

    return response


async def wrap_chat_completion_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction or kwargs.get("stream", False):
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    request_message_list = kwargs.get("messages", [])

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", None) if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

    # Get conversation ID off of the transaction
    custom_attrs_dict = transaction._custom_params
    conversation_id = custom_attrs_dict.get("llm.conversation_id", "")

    settings = transaction.settings if transaction.settings is not None else global_settings()
    app_name = settings.app_name
    completion_id = str(uuid.uuid4())

    function_name = wrapped.__name__

    with FunctionTrace(name=function_name, group="Llm/completion/OpenAI") as ft:
        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id", "")
        trace_id = available_metadata.get("trace.id", "")

        try:
            return_val = await wrapped(*args, **kwargs)
        except Exception as exc:
            if OPENAI_V1:
                response = getattr(exc, "response", "")
                response_headers = getattr(response, "headers", "")
                exc_organization = response_headers.get("openai-organization", "") if response_headers else ""
                # There appears to be a bug here in openai v1 where despite having code,
                # param, etc in the error response, they are not populated on the exception
                # object so grab them from the response body object instead.
                body = getattr(exc, "body", {}) or {}
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "status_code", "") or "",
                    "error.message": body.get("message", "") or "",
                    "error.code": body.get("code", "") or "",
                    "error.param": body.get("param", "") or "",
                    "completion_id": completion_id,
                }
            else:
                exc_organization = getattr(exc, "organization", "")
                notice_error_attributes = {
                    "http.statusCode": getattr(exc, "http_status", ""),
                    "error.message": getattr(exc, "_message", ""),
                    "error.code": getattr(getattr(exc, "error", ""), "code", ""),
                    "error.param": getattr(exc, "param", ""),
                    "completion_id": completion_id,
                }
            # Override the default message if it is not empty.
            message = notice_error_attributes.pop("error.message")
            if message:
                exc._nr_message = message

            ft.notice_error(
                attributes=notice_error_attributes,
            )
            # Gather attributes to add to embedding summary event in error context
            error_chat_completion_dict = {
                "id": completion_id,
                "appName": app_name,
                "conversation_id": conversation_id,
                "api_key_last_four_digits": api_key_last_four_digits,
                "span_id": span_id,
                "trace_id": trace_id,
                "transaction_id": transaction.guid,
                "response.number_of_messages": len(request_message_list),
                "request.model": kwargs.get("model") or kwargs.get("engine") or "",
                "request.temperature": kwargs.get("temperature", ""),
                "request.max_tokens": kwargs.get("max_tokens", ""),
                "vendor": "openAI",
                "ingest_source": "Python",
                "response.organization": "" if exc_organization is None else exc_organization,
                "duration": ft.duration,
                "error": True,
            }
            transaction.record_custom_event("LlmChatCompletionSummary", error_chat_completion_dict)

            create_chat_completion_message_event(
                transaction,
                app_name,
                request_message_list,
                completion_id,
                span_id,
                trace_id,
                "",
                None,
                "",
                conversation_id,
                None,
            )

            raise

    if not return_val:
        return return_val

    # At this point, we have a response so we can grab attributes only available on the response object
    response_headers = getattr(return_val, "_nr_response_headers", None)
    # In v1, response objects are pydantic models so this function call converts the
    # object back to a dictionary for backwards compatibility.
    response = return_val
    if OPENAI_V1:
        response = response.model_dump()

    response_model = response.get("model", "") or ""
    response_id = response.get("id")
    request_id = response_headers.get("x-request-id", "") if response_headers else ""

    response_usage = response.get("usage", {}) or {}

    messages = kwargs.get("messages", []) or []
    choices = response.get("choices", []) or []
    organization = (
        response_headers.get("openai-organization", "") if OPENAI_V1 else getattr(response, "organization", "")
    )

    full_chat_completion_summary_dict = {
        "id": completion_id,
        "appName": app_name,
        "conversation_id": conversation_id,
        "api_key_last_four_digits": api_key_last_four_digits,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "request.temperature": kwargs.get("temperature", ""),
        "request.max_tokens": kwargs.get("max_tokens", ""),
        "vendor": "openAI",
        "ingest_source": "Python",
        "request_id": request_id,
        "duration": ft.duration,
        "response.model": response_model,
        "response.organization": organization,
        "response.usage.completion_tokens": response_usage.get("completion_tokens", "") if response_usage else "",
        "response.usage.total_tokens": response_usage.get("total_tokens", "") if response_usage else "",
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens", "") if response_usage else "",
        "response.choices.finish_reason": choices[0].get("finish_reason", "") if choices else "",
        "response.api_type": getattr(response, "api_type", ""),
        "response.headers.llmVersion": response_headers.get("openai-version", ""),
        "response.headers.ratelimitLimitRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-requests", True
        ),
        "response.headers.ratelimitLimitTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-tokens", True
        ),
        "response.headers.ratelimitResetTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-tokens", False
        ),
        "response.headers.ratelimitResetRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-requests", False
        ),
        "response.headers.ratelimitRemainingTokens": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-tokens", True
        ),
        "response.headers.ratelimitRemainingRequests": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-requests", True
        ),
        "response.headers.ratelimitLimitTokensUsageBased": check_rate_limit_header(
            response_headers, "x-ratelimit-limit-tokens_usage_based", True
        ),
        "response.headers.ratelimitResetTokensUsageBased": check_rate_limit_header(
            response_headers, "x-ratelimit-reset-tokens_usage_based", False
        ),
        "response.headers.ratelimitRemainingTokensUsageBased": check_rate_limit_header(
            response_headers, "x-ratelimit-remaining-tokens_usage_based", True
        ),
        "response.number_of_messages": len(messages) + len(choices),
    }

    transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)

    input_message_list = list(messages)
    output_message_list = [choices[0].get("message", "")] if choices else None

    message_ids = create_chat_completion_message_event(
        transaction,
        settings.app_name,
        input_message_list,
        completion_id,
        span_id,
        trace_id,
        response_model,
        response_id,
        request_id,
        conversation_id,
        output_message_list,
    )

    # Cache message ids on transaction for retrieval after open ai call completion.
    if not hasattr(transaction, "_nr_message_ids"):
        transaction._nr_message_ids = {}
    transaction._nr_message_ids[response_id] = message_ids

    return return_val


def wrap_convert_to_openai_object(wrapped, instance, args, kwargs):
    resp = args[0]
    returned_response = wrapped(*args, **kwargs)

    if isinstance(resp, openai.openai_response.OpenAIResponse):
        setattr(returned_response, "_nr_response_headers", getattr(resp, "_headers", {}))

    return returned_response


def bind_base_client_process_response(
    cast_to,
    options,
    response,
    stream,
    stream_cls,
):
    return response


def wrap_base_client_process_response(wrapped, instance, args, kwargs):
    response = bind_base_client_process_response(*args, **kwargs)
    nr_response_headers = getattr(response, "headers")

    return_val = wrapped(*args, **kwargs)
    # Obtain response headers for v1
    return_val._nr_response_headers = nr_response_headers
    return return_val


def instrument_openai_util(module):
    if hasattr(module, "convert_to_openai_object"):
        wrap_function_wrapper(module, "convert_to_openai_object", wrap_convert_to_openai_object)
        # This is to mark where we instrument so the SDK knows not to instrument them
        # again.
        setattr(module.convert_to_openai_object, "_nr_wrapped", True)


def instrument_openai_api_resources_embedding(module):
    if hasattr(module, "Embedding"):
        if hasattr(module.Embedding, "create"):
            wrap_function_wrapper(module, "Embedding.create", wrap_embedding_sync)
        if hasattr(module.Embedding, "acreate"):
            wrap_function_wrapper(module, "Embedding.acreate", wrap_embedding_async)
        # This is to mark where we instrument so the SDK knows not to instrument them
        # again.
        setattr(module.Embedding, "_nr_wrapped", True)


def instrument_openai_api_resources_chat_completion(module):
    if hasattr(module, "ChatCompletion"):
        if hasattr(module.ChatCompletion, "create"):
            wrap_function_wrapper(module, "ChatCompletion.create", wrap_chat_completion_sync)
        if hasattr(module.ChatCompletion, "acreate"):
            wrap_function_wrapper(module, "ChatCompletion.acreate", wrap_chat_completion_async)
        # This is to mark where we instrument so the SDK knows not to instrument them
        # again.
        setattr(module.ChatCompletion, "_nr_wrapped", True)


def instrument_openai_resources_chat_completions(module):
    if hasattr(module.Completions, "create"):
        wrap_function_wrapper(module, "Completions.create", wrap_chat_completion_sync)
    if hasattr(module.AsyncCompletions, "create"):
        wrap_function_wrapper(module, "AsyncCompletions.create", wrap_chat_completion_async)


def instrument_openai_resources_embeddings(module):
    if hasattr(module, "Embeddings"):
        if hasattr(module.Embeddings, "create"):
            wrap_function_wrapper(module, "Embeddings.create", wrap_embedding_sync)

    if hasattr(module, "AsyncEmbeddings"):
        if hasattr(module.Embeddings, "create"):
            wrap_function_wrapper(module, "AsyncEmbeddings.create", wrap_embedding_async)


def instrument_openai_base_client(module):
    if hasattr(module.BaseClient, "_process_response"):
        wrap_function_wrapper(module, "BaseClient._process_response", wrap_base_client_process_response)
