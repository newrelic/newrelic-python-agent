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
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

OPENAI_VERSION = get_package_version("openai")


def openai_error_attributes(exception, request_args):
    api_key = getattr(openai, "api_key", None)
    api_key_last_four_digits = f"sk-{api_key[-4:]}" if api_key else ""
    number_of_messages = len(request_args.get("messages", []))

    error_attributes = {
        "api_key_last_four_digits": api_key_last_four_digits,
        "request.model": request_args.get("model") or request_args.get("engine") or "",
        "request.temperature": request_args.get("temperature", ""),
        "request.max_tokens": request_args.get("max_tokens", ""),
        "vendor": "openAI",
        "ingest_source": "Python",
        "response.organization": getattr(exception, "organization", ""),
        "response.number_of_messages": number_of_messages,
        "http.statusCode": getattr(exception, "http_status", ""),
        "error.message": getattr(exception, "_message", ""),
        "error.code": getattr(getattr(exception, "error", ""), "code", ""),
        "error.param": getattr(exception, "param", ""),
    }
    return error_attributes


def wrap_embedding_create(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            error_attributes = openai_error_attributes(exc, kwargs)
            exc._nr_message = error_attributes.pop("error.message")
            ft.notice_error(
                attributes=error_attributes,
            )
            raise

    if not response:
        return response

    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")
    embedding_id = str(uuid.uuid4())

    response_headers = getattr(response, "_nr_response_headers", None)
    request_id = response_headers.get("x-request-id", "") if response_headers else ""
    response_model = response.get("model", "")
    response_usage = response.get("usage", {})

    settings = transaction.settings if transaction.settings is not None else global_settings()

    embedding_dict = {
        "id": embedding_id,
        "appName": settings.app_name,
        "span_id": span_id,
        "trace_id": trace_id,
        "request_id": request_id,
        "transaction_id": transaction._transaction_id,
        "input": kwargs.get("input", ""),
        "api_key_last_four_digits": f"sk-{response.api_key[-4:]}",
        "duration": ft.duration,
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "response.model": response_model,
        "response.organization": response.organization,
        "response.api_type": response.api_type,
        "response.usage.total_tokens": response_usage.get("total_tokens", "") if any(response_usage) else "",
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens", "") if any(response_usage) else "",
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

    transaction.record_custom_event("LlmEmbedding", embedding_dict)

    return response


def wrap_chat_completion_create(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            error_attributes = openai_error_attributes(exc, kwargs)
            exc._nr_message = error_attributes.pop("error.message")
            ft.notice_error(
                attributes=error_attributes,
            )
            raise

    if not response:
        return response

    custom_attrs_dict = transaction._custom_params
    conversation_id = custom_attrs_dict.get("conversation_id", "")

    chat_completion_id = str(uuid.uuid4())
    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")

    response_headers = getattr(response, "_nr_response_headers", None)
    response_model = response.get("model", "")
    settings = transaction.settings if transaction.settings is not None else global_settings()
    response_id = response.get("id")
    request_id = response_headers.get("x-request-id", "")

    api_key = getattr(response, "api_key", None)
    response_usage = response.get("usage", {})

    messages = kwargs.get("messages", [])
    choices = response.get("choices", [])

    chat_completion_summary_dict = {
        "id": chat_completion_id,
        "appName": settings.app_name,
        "conversation_id": conversation_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction._transaction_id,
        "request_id": request_id,
        "api_key_last_four_digits": f"sk-{api_key[-4:]}" if api_key else "",
        "duration": ft.duration,
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "response.model": response_model,
        "response.organization": getattr(response, "organization", ""),
        "response.usage.completion_tokens": response_usage.get("completion_tokens", "") if any(response_usage) else "",
        "response.usage.total_tokens": response_usage.get("total_tokens", "") if any(response_usage) else "",
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens", "") if any(response_usage) else "",
        "request.temperature": kwargs.get("temperature", ""),
        "request.max_tokens": kwargs.get("max_tokens", ""),
        "response.choices.finish_reason": choices[0].finish_reason if choices else "",
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
        "vendor": "openAI",
        "ingest_source": "Python",
        "response.number_of_messages": len(messages) + len(choices),
    }

    transaction.record_custom_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    message_list = list(messages)
    if choices:
        message_list.extend([choices[0].message])

    message_ids = create_chat_completion_message_event(
        transaction,
        settings.app_name,
        message_list,
        chat_completion_id,
        span_id,
        trace_id,
        response_model,
        response_id,
        request_id,
        conversation_id,
    )

    # Cache message ids on transaction for retrieval after open ai call completion.
    if not hasattr(transaction, "_nr_message_ids"):
        transaction._nr_message_ids = {}
    transaction._nr_message_ids[response_id] = message_ids

    return response


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
    message_list,
    chat_completion_id,
    span_id,
    trace_id,
    response_model,
    response_id,
    request_id,
    conversation_id,
):
    message_ids = []
    for index, message in enumerate(message_list):
        message_id = "%s-%s" % (response_id, index)
        message_ids.append(message_id)
        chat_completion_message_dict = {
            "id": message_id,
            "appName": app_name,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction._transaction_id,
            "content": message.get("content", ""),
            "role": message.get("role", ""),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": response_model,
            "vendor": "openAI",
            "ingest_source": "Python",
        }
        
        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_message_dict)

    return (conversation_id, request_id, message_ids)


async def wrap_embedding_acreate(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        try:
            response = await wrapped(*args, **kwargs)
        except Exception as exc:
            error_attributes = openai_error_attributes(exc, kwargs)
            exc._nr_message = error_attributes.pop("error.message")
            ft.notice_error(
                attributes=error_attributes,
            )
            raise

    if not response:
        return response

    embedding_id = str(uuid.uuid4())
    response_headers = getattr(response, "_nr_response_headers", None)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")

    api_key = getattr(response, "api_key", None)
    usage = response.get("usage")
    total_tokens = ""
    prompt_tokens = ""
    if usage:
        total_tokens = usage.get("total_tokens", "")
        prompt_tokens = usage.get("prompt_tokens", "")

    embedding_dict = {
        "id": embedding_id,
        "duration": ft.duration,
        "api_key_last_four_digits": f"sk-{api_key[-4:]}" if api_key else "",
        "request_id": response_headers.get("x-request-id", ""),
        "input": kwargs.get("input", ""),
        "response.api_type": getattr(response, "api_type", ""),
        "response.organization": getattr(response, "organization", ""),
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "response.model": response.get("model", ""),
        "appName": settings.app_name,
        "trace_id": trace_id,
        "transaction_id": transaction._transaction_id,
        "span_id": span_id,
        "response.usage.total_tokens": total_tokens,
        "response.usage.prompt_tokens": prompt_tokens,
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

    transaction.record_custom_event("LlmEmbedding", embedding_dict)

    return response


async def wrap_chat_completion_acreate(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return await wrapped(*args, **kwargs)

    transaction.add_ml_model_info("OpenAI", OPENAI_VERSION)

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        try:
            response = await wrapped(*args, **kwargs)
        except Exception as exc:
            error_attributes = openai_error_attributes(exc, kwargs)
            exc._nr_message = error_attributes.pop("error.message")
            ft.notice_error(
                attributes=error_attributes,
            )
            raise

    if not response:
        return response

    conversation_id = transaction._custom_params.get("conversation_id", "")

    chat_completion_id = str(uuid.uuid4())
    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")

    response_headers = getattr(response, "_nr_response_headers", None)
    response_model = response.get("model", "")
    settings = transaction.settings if transaction.settings is not None else global_settings()
    response_id = response.get("id")
    request_id = response_headers.get("x-request-id", "")

    api_key = getattr(response, "api_key", None)
    usage = response.get("usage")
    total_tokens = ""
    prompt_tokens = ""
    completion_tokens = ""
    if usage:
        total_tokens = usage.get("total_tokens", "")
        prompt_tokens = usage.get("prompt_tokens", "")
        completion_tokens = usage.get("completion_tokens", "")

    messages = kwargs.get("messages", [])
    choices = response.get("choices", [])

    chat_completion_summary_dict = {
        "id": chat_completion_id,
        "appName": settings.app_name,
        "conversation_id": conversation_id,
        "request_id": request_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction._transaction_id,
        "api_key_last_four_digits": f"sk-{api_key[-4:]}" if api_key else "",
        "duration": ft.duration,
        "request.model": kwargs.get("model") or kwargs.get("engine") or "",
        "response.model": response_model,
        "response.organization": getattr(response, "organization", ""),
        "response.usage.completion_tokens": completion_tokens,
        "response.usage.total_tokens": total_tokens,
        "response.usage.prompt_tokens": prompt_tokens,
        "response.number_of_messages": len(messages) + len(choices),
        "request.temperature": kwargs.get("temperature", ""),
        "request.max_tokens": kwargs.get("max_tokens", ""),
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
        "vendor": "openAI",
        "ingest_source": "Python",
    }

    transaction.record_custom_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    message_list = list(messages)
    if choices:
        message_list.extend([choices[0].message])

    message_ids = create_chat_completion_message_event(
        transaction,
        settings.app_name,
        message_list,
        chat_completion_id,
        span_id,
        trace_id,
        response_model,
        response_id,
        request_id,
        conversation_id,
    )

    # Cache message ids on transaction for retrieval after open ai call completion.
    if not hasattr(transaction, "_nr_message_ids"):
        transaction._nr_message_ids = {}
    transaction._nr_message_ids[response_id] = message_ids

    return response


def wrap_convert_to_openai_object(wrapped, instance, args, kwargs):
    resp = args[0]
    returned_response = wrapped(*args, **kwargs)

    if isinstance(resp, openai.openai_response.OpenAIResponse):
        setattr(returned_response, "_nr_response_headers", getattr(resp, "_headers", {}))

    return returned_response


def instrument_openai_util(module):
    wrap_function_wrapper(module, "convert_to_openai_object", wrap_convert_to_openai_object)


def instrument_openai_api_resources_embedding(module):
    if hasattr(module.Embedding, "create"):
        wrap_function_wrapper(module, "Embedding.create", wrap_embedding_create)
    if hasattr(module.Embedding, "acreate"):
        wrap_function_wrapper(module, "Embedding.acreate", wrap_embedding_acreate)


def instrument_openai_api_resources_chat_completion(module):
    if hasattr(module.ChatCompletion, "create"):
        wrap_function_wrapper(module, "ChatCompletion.create", wrap_chat_completion_create)
    if hasattr(module.ChatCompletion, "acreate"):
        wrap_function_wrapper(module, "ChatCompletion.acreate", wrap_chat_completion_acreate)
