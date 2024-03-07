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

import sys
import uuid

import openai

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

OPENAI_VERSION = get_package_version("openai")
OPENAI_VERSION_TUPLE = tuple(map(int, OPENAI_VERSION.split(".")))
OPENAI_V1 = OPENAI_VERSION_TUPLE >= (1,)


def wrap_embedding_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction or kwargs.get("stream", False):
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)
    transaction._add_agent_attribute("llm", True)

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", "") if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

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
                "request.model": kwargs.get("model") or kwargs.get("engine") or "",
                "vendor": "openAI",
                "ingest_source": "Python",
                "response.organization": "" if exc_organization is None else exc_organization,
                "duration": ft.duration,
                "error": True,
            }

            if settings.ai_monitoring.record_content.enabled:
                error_embedding_dict.update({"input": kwargs.get("input", "")})

            error_embedding_dict.update(llm_metadata_dict)

            transaction.record_custom_event("LlmEmbedding", error_embedding_dict)

            raise

    if not response:
        return response

    response_headers = getattr(response, "_nr_response_headers", {})

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

    if settings.ai_monitoring.record_content.enabled:
        full_embedding_response_dict.update({"input": kwargs.get("input", "")})

    full_embedding_response_dict.update(llm_metadata_dict)

    transaction.record_custom_event("LlmEmbedding", full_embedding_response_dict)

    return response


def wrap_chat_completion_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)
    transaction._add_agent_attribute("llm", True)
    if not settings.ai_monitoring.streaming.enabled:
        transaction.record_custom_metric("Supportability/Python/ML/Streaming/Disabled", 1)

    request_message_list = kwargs.get("messages", [])

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", None) if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    app_name = settings.app_name
    completion_id = str(uuid.uuid4())

    function_name = wrapped.__name__

    ft = FunctionTrace(name=function_name, group="Llm/completion/OpenAI")
    ft.__enter__()
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

        error_chat_completion_dict.update(llm_metadata_dict)

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
            llm_metadata_dict,
            None,
        )

        ft.__exit__(*sys.exc_info())
        raise

    stream = kwargs.get("stream", False)
    # If response is not a stream generator or stream monitoring is disabled, we exit
    # the function trace now.
    if not stream or not settings.ai_monitoring.streaming.enabled:
        ft.__exit__(None, None, None)

    # If the return value is empty or stream monitoring is disabled return early.
    if not return_val or not settings.ai_monitoring.streaming.enabled:
        return return_val

    if stream:
        # The function trace will be exited when in the final iteration of the response
        # generator.
        setattr(return_val, "_nr_ft", ft)
        setattr(return_val, "_nr_openai_attrs", getattr(return_val, "_nr_openai_attrs", {}))
        return_val._nr_openai_attrs["messages"] = kwargs.get("messages", [])
        return_val._nr_openai_attrs["temperature"] = kwargs.get("temperature", "")
        return_val._nr_openai_attrs["max_tokens"] = kwargs.get("max_tokens", "")
        return_val._nr_openai_attrs["request.model"] = kwargs.get("model") or kwargs.get("engine") or ""
        return_val._nr_openai_attrs["api_key_last_four_digits"] = api_key_last_four_digits
        return return_val

    # If response is not a stream generator, record the event data.
    # At this point, we have a response so we can grab attributes only available on the response object
    response_headers = getattr(return_val, "_nr_response_headers", {})
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

    full_chat_completion_summary_dict.update(llm_metadata_dict)

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
        llm_metadata_dict,
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
    llm_metadata_dict,
    output_message_list,
):
    settings = transaction.settings if transaction.settings is not None else global_settings()

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
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction.guid,
            "role": message.get("role", ""),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": response_model if response_model else "",
            "vendor": "openAI",
            "ingest_source": "Python",
        }

        if settings.ai_monitoring.record_content.enabled:
            chat_completion_input_message_dict.update({"content": message_content})

        chat_completion_input_message_dict.update(llm_metadata_dict)

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
                "request_id": request_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "transaction_id": transaction.guid,
                "role": message.get("role", ""),
                "completion_id": chat_completion_id,
                "sequence": index,
                "response.model": response_model if response_model else "",
                "vendor": "openAI",
                "ingest_source": "Python",
                "is_response": True,
            }

            if settings.ai_monitoring.record_content.enabled:
                chat_completion_output_message_dict.update({"content": message_content})

            chat_completion_output_message_dict.update(llm_metadata_dict)

            transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_output_message_dict)

    # TODO: Remove this logic when message-based feedback is removed from the agent
    return (request_id, message_ids)


async def wrap_embedding_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction or kwargs.get("stream", False):
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)
    transaction._add_agent_attribute("llm", True)

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", "") if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

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
                "request.model": kwargs.get("model") or kwargs.get("engine") or "",
                "vendor": "openAI",
                "ingest_source": "Python",
                "response.organization": "" if exc_organization is None else exc_organization,
                "duration": ft.duration,
                "error": True,
            }

            if settings.ai_monitoring.record_content.enabled:
                error_embedding_dict.update({"input": kwargs.get("input", "")})

            error_embedding_dict.update(llm_metadata_dict)

            transaction.record_custom_event("LlmEmbedding", error_embedding_dict)

            raise

    if not response:
        return response

    response_headers = getattr(response, "_nr_response_headers", {})

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

    if settings.ai_monitoring.record_content.enabled:
        full_embedding_response_dict.update({"input": kwargs.get("input", "")})

    full_embedding_response_dict.update(llm_metadata_dict)

    transaction.record_custom_event("LlmEmbedding", full_embedding_response_dict)

    return response


async def wrap_chat_completion_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)
    transaction._add_agent_attribute("llm", True)
    if not settings.ai_monitoring.streaming.enabled:
        transaction.record_custom_metric("Supportability/Python/ML/Streaming/Disabled", 1)

    request_message_list = kwargs.get("messages", [])

    # Get API key without using the response so we can store it before the response is returned in case of errors
    api_key = getattr(instance._client, "api_key", None) if OPENAI_V1 else getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""

    span_id = None
    trace_id = None

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    app_name = settings.app_name
    completion_id = str(uuid.uuid4())

    function_name = wrapped.__name__
    ft = FunctionTrace(name=function_name, group="Llm/completion/OpenAI")
    ft.__enter__()
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

        error_chat_completion_dict.update(llm_metadata_dict)

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
            llm_metadata_dict,
            None,
        )

        ft.__exit__(*sys.exc_info())
        raise

    stream = kwargs.get("stream", False)
    # If response is not a stream generator or stream monitoring is disabled, we exit
    # the function trace now.
    if not stream or not settings.ai_monitoring.streaming.enabled:
        ft.__exit__(None, None, None)

    # If the return value is empty or stream monitoring is diabled exit early.
    if not return_val or not settings.ai_monitoring.streaming.enabled:
        return return_val

    if stream:
        # The function trace will be exited when in the final iteration of the response
        # generator.
        setattr(return_val, "_nr_ft", ft)
        setattr(return_val, "_nr_openai_attrs", getattr(return_val, "_nr_openai_attrs", {}))
        return_val._nr_openai_attrs["messages"] = kwargs.get("messages", [])
        return_val._nr_openai_attrs["temperature"] = kwargs.get("temperature", "")
        return_val._nr_openai_attrs["max_tokens"] = kwargs.get("max_tokens", "")
        return_val._nr_openai_attrs["request.model"] = kwargs.get("model") or kwargs.get("engine") or ""
        return_val._nr_openai_attrs["api_key_last_four_digits"] = api_key_last_four_digits
        return return_val

    # If response is not a stream generator, record the event data.
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

    full_chat_completion_summary_dict.update(llm_metadata_dict)

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
        llm_metadata_dict,
        output_message_list,
    )

    # Cache message ids on transaction for retrieval after open ai call completion.
    if not hasattr(transaction, "_nr_message_ids"):
        transaction._nr_message_ids = {}
    transaction._nr_message_ids[response_id] = message_ids

    return return_val


def wrap_convert_to_openai_object(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    resp = args[0]
    returned_response = wrapped(*args, **kwargs)

    if isinstance(returned_response, openai.openai_object.OpenAIObject) and isinstance(
        resp, openai.openai_response.OpenAIResponse
    ):
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


def wrap_base_client_process_response_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    response = bind_base_client_process_response(*args, **kwargs)
    nr_response_headers = getattr(response, "headers")

    return_val = wrapped(*args, **kwargs)
    # Obtain response headers for v1
    return_val._nr_response_headers = nr_response_headers
    return return_val


async def wrap_base_client_process_response_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    response = bind_base_client_process_response(*args, **kwargs)
    nr_response_headers = getattr(response, "headers")

    return_val = await wrapped(*args, **kwargs)
    # Obtain reponse headers for v1
    return_val._nr_response_headers = nr_response_headers
    return return_val


def instrument_openai_util(module):
    if hasattr(module, "convert_to_openai_object"):
        wrap_function_wrapper(module, "convert_to_openai_object", wrap_convert_to_openai_object)
        # This is to mark where we instrument so the SDK knows not to instrument them
        # again.
        setattr(module.convert_to_openai_object, "_nr_wrapped", True)


class GeneratorProxy(ObjectProxy):
    def __init__(self, wrapped):
        super(GeneratorProxy, self).__init__(wrapped)

    def __iter__(self):
        return self

    def __next__(self):
        transaction = current_transaction()
        if not transaction:
            return self.__wrapped__.__next__()

        return_val = None
        try:
            return_val = self.__wrapped__.__next__()
            record_stream_chunk(self, return_val)
        except StopIteration as e:
            record_events_on_stop_iteration(self, transaction)
            raise
        except Exception as exc:
            record_error(self, transaction, exc)
            raise
        return return_val

    def close(self):
        return super(GeneratorProxy, self).close()


def record_stream_chunk(self, return_val):
    if return_val:
        if OPENAI_V1:
            if getattr(return_val, "data", "").startswith("[DONE]"):
                return
            return_val = return_val.json()
            self._nr_openai_attrs["response_headers"] = getattr(self, "_nr_response_headers", {})
        else:
            self._nr_openai_attrs["response_headers"] = getattr(return_val, "_nr_response_headers", {})
        choices = return_val.get("choices", [])
        self._nr_openai_attrs["response.model"] = return_val.get("model", "")
        self._nr_openai_attrs["id"] = return_val.get("id", "")
        self._nr_openai_attrs["response.organization"] = return_val.get("organization", "")
        if choices:
            delta = choices[0].get("delta", {})
            if delta:
                self._nr_openai_attrs["content"] = self._nr_openai_attrs.get("content", "") + (
                    delta.get("content") or ""
                )
                self._nr_openai_attrs["role"] = self._nr_openai_attrs.get("role", None) or delta.get("role")
            self._nr_openai_attrs["finish_reason"] = choices[0].get("finish_reason", "")


def record_events_on_stop_iteration(self, transaction):
    if hasattr(self, "_nr_ft"):
        openai_attrs = getattr(self, "_nr_openai_attrs", {})
        self._nr_ft.__exit__(None, None, None)

        # If there are no openai attrs exit early as there's no data to record.
        if not openai_attrs:
            return

        message_ids = record_streaming_chat_completion_events(self, transaction, openai_attrs)
        # Clear cached data as this can be very large.
        # Note this is also important for not reporting the events twice. In openai v1
        # there are two loops around the iterator, the second is meant to clear the
        # stream since there is a condition where the iterator may exit before all the
        # stream contents is read. This results in StopIteration being raised twice
        # instead of once at the end of the loop.
        self._nr_openai_attrs = {}
        # Cache message ids on transaction for retrieval after open ai call completion.
        if not hasattr(transaction, "_nr_message_ids"):
            transaction._nr_message_ids = {}
        response_id = openai_attrs.get("id", None)
        transaction._nr_message_ids[response_id] = message_ids


def record_error(self, transaction, exc):
    if hasattr(self, "_nr_ft"):
        openai_attrs = getattr(self, "_nr_openai_attrs", {})

        # If there are no openai attrs exit early as there's no data to record.
        if not openai_attrs:
            self._nr_ft.__exit__(*sys.exc_info())
            return

        record_streaming_chat_completion_events_error(self, transaction, openai_attrs, exc)


def record_streaming_chat_completion_events_error(self, transaction, openai_attrs, exc):
    chat_completion_id = str(uuid.uuid4())
    if OPENAI_V1:
        response = getattr(exc, "response", "")
        response_headers = getattr(response, "headers", "")
        organization = response_headers.get("openai-organization", "") if response_headers else ""
        # There appears to be a bug here in openai v1 where despite having code,
        # param, etc in the error response, they are not populated on the exception
        # object so grab them from the response body object instead.
        body = getattr(exc, "body", {}) or {}
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "status_code", "") or "",
            "error.message": body.get("message", "") or "",
            "error.code": body.get("code", "") or "",
            "error.param": body.get("param", "") or "",
            "completion_id": chat_completion_id,
        }
    else:
        organization = getattr(exc, "organization", "")
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "http_status", ""),
            "error.message": getattr(exc, "_message", ""),
            "error.code": getattr(getattr(exc, "error", ""), "code", ""),
            "error.param": getattr(exc, "param", ""),
            "completion_id": chat_completion_id,
        }
    message = notice_error_attributes.pop("error.message")
    if message:
        exc._nr_message = message
    self._nr_ft.notice_error(
        attributes=notice_error_attributes,
    )
    self._nr_ft.__exit__(*sys.exc_info())
    content = openai_attrs.get("content", None)
    role = openai_attrs.get("role")

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")

    response_headers = openai_attrs.get("response_headers", {})
    settings = transaction.settings if transaction.settings is not None else global_settings()
    response_id = openai_attrs.get("id", None)
    request_id = response_headers.get("x-request-id", "")

    api_key_last_four_digits = openai_attrs.get("api_key_last_four_digits", "")

    messages = openai_attrs.get("messages", [])

    chat_completion_summary_dict = {
        "id": chat_completion_id,
        "appName": settings.app_name,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "api_key_last_four_digits": api_key_last_four_digits,
        "duration": self._nr_ft.duration,
        "request.model": openai_attrs.get("request.model", ""),
        # Usage tokens are not supported in streaming for now.
        "request.temperature": openai_attrs.get("temperature", ""),
        "request.max_tokens": openai_attrs.get("max_tokens", ""),
        "vendor": "openAI",
        "ingest_source": "Python",
        "response.number_of_messages": len(messages) + (1 if content else 0),
        "response.organization": organization,
        "error": True,
    }

    chat_completion_summary_dict.update(llm_metadata_dict)

    transaction.record_custom_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    output_message_list = []
    if content:
        output_message_list = [{"content": content, "role": role}]

    return create_chat_completion_message_event(
        transaction,
        settings.app_name,
        list(messages),
        chat_completion_id,
        span_id,
        trace_id,
        openai_attrs.get("response.model", ""),
        response_id,
        request_id,
        llm_metadata_dict,
        output_message_list,
    )


def record_streaming_chat_completion_events(self, transaction, openai_attrs):
    content = openai_attrs.get("content", None)
    role = openai_attrs.get("role")

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    chat_completion_id = str(uuid.uuid4())
    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")

    response_headers = openai_attrs.get("response_headers", {})
    settings = transaction.settings if transaction.settings is not None else global_settings()
    response_id = openai_attrs.get("id", None)
    request_id = response_headers.get("x-request-id", "")
    organization = response_headers.get("openai-organization", "")

    api_key_last_four_digits = openai_attrs.get("api_key_last_four_digits", "")

    messages = openai_attrs.get("messages", [])

    chat_completion_summary_dict = {
        "id": chat_completion_id,
        "appName": settings.app_name,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "request_id": request_id,
        "api_key_last_four_digits": api_key_last_four_digits,
        "duration": self._nr_ft.duration,
        "request.model": openai_attrs.get("request.model", ""),
        "response.model": openai_attrs.get("response.model", ""),
        "response.organization": organization,
        # Usage tokens are not supported in streaming for now.
        "request.temperature": openai_attrs.get("temperature", ""),
        "request.max_tokens": openai_attrs.get("max_tokens", ""),
        "response.choices.finish_reason": openai_attrs.get("finish_reason", ""),
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
        "response.number_of_messages": len(messages) + (1 if content else 0),
    }

    chat_completion_summary_dict.update(llm_metadata_dict)

    transaction.record_custom_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    output_message_list = []
    if content:
        output_message_list = [{"content": content, "role": role}]

    return create_chat_completion_message_event(
        transaction,
        settings.app_name,
        list(messages),
        chat_completion_id,
        span_id,
        trace_id,
        openai_attrs.get("response.model", ""),
        response_id,
        request_id,
        llm_metadata_dict,
        output_message_list,
    )


class AsyncGeneratorProxy(ObjectProxy):
    def __init__(self, wrapped):
        super(AsyncGeneratorProxy, self).__init__(wrapped)

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
            record_stream_chunk(self, return_val)
        except StopAsyncIteration as e:
            record_events_on_stop_iteration(self, transaction)
            raise
        except Exception as exc:
            record_error(self, transaction, exc)
            raise
        return return_val

    async def aclose(self):
        return await super(AsyncGeneratorProxy, self).aclose()


def wrap_engine_api_resource_create_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    stream = bound_args["params"].get("stream", False)

    return_val = wrapped(*args, **kwargs)

    if stream and settings.ai_monitoring.streaming.enabled:
        return GeneratorProxy(return_val)
    else:
        return return_val


def wrap_stream_iter_events_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled or not settings.ai_monitoring.streaming.enabled:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)

    return_val = wrapped(*args, **kwargs)
    proxied_return_val = GeneratorProxy(return_val)
    # Pass the nr attributes to the generator proxy.
    proxied_return_val._nr_ft = instance._nr_ft
    proxied_return_val._nr_response_headers = instance._nr_response_headers
    proxied_return_val._nr_openai_attrs = instance._nr_openai_attrs
    return proxied_return_val


async def wrap_engine_api_resource_create_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    stream = bound_args["params"].get("stream", False)

    return_val = await wrapped(*args, **kwargs)

    if stream and settings.ai_monitoring.streaming.enabled:
        return AsyncGeneratorProxy(return_val)
    else:
        return return_val


def wrap_stream_iter_events_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled or not settings.ai_monitoring.streaming.enabled:
        return wrapped(*args, **kwargs)

    proxied_return_val = AsyncGeneratorProxy(wrapped(*args, **kwargs))
    # Pass the nr attributes to the generator proxy.
    proxied_return_val._nr_ft = instance._nr_ft
    proxied_return_val._nr_response_headers = instance._nr_response_headers
    proxied_return_val._nr_openai_attrs = instance._nr_openai_attrs
    return proxied_return_val


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
        wrap_function_wrapper(module, "BaseClient._process_response", wrap_base_client_process_response_sync)
    else:
        if hasattr(module.SyncAPIClient, "_process_response"):
            wrap_function_wrapper(module, "SyncAPIClient._process_response", wrap_base_client_process_response_sync)
        if hasattr(module.AsyncAPIClient, "_process_response"):
            wrap_function_wrapper(module, "AsyncAPIClient._process_response", wrap_base_client_process_response_async)


def instrument_openai_api_resources_abstract_engine_api_resource(module):
    if hasattr(module.EngineAPIResource, "create"):
        wrap_function_wrapper(module, "EngineAPIResource.create", wrap_engine_api_resource_create_sync)
    if hasattr(module.EngineAPIResource, "acreate"):
        wrap_function_wrapper(module, "EngineAPIResource.acreate", wrap_engine_api_resource_create_async)


def instrument_openai__streaming(module):
    if hasattr(module, "Stream"):
        if hasattr(module.Stream, "_iter_events"):
            wrap_function_wrapper(module, "Stream._iter_events", wrap_stream_iter_events_sync)
    if hasattr(module, "AsyncStream"):
        if hasattr(module.AsyncStream, "_iter_events"):
            wrap_function_wrapper(module, "AsyncStream._iter_events", wrap_stream_iter_events_async)
