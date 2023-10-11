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

import openai
import uuid
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.core.config import global_settings
from newrelic.common.object_names import callable_name
from newrelic.core.attribute import MAX_LOG_MESSAGE_LENGTH


def wrap_embedding_create(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        response = wrapped(*args, **kwargs)

    if not response:
        return

    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")
    embedding_id = str(uuid.uuid4())
    response_headers = getattr(response, "_nr_response_headers")
    settings = transaction.settings if transaction.settings is not None else global_settings()


    embedding_dict = {
        "id": embedding_id,
        "appName": settings.app_name,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction._transaction_id,
        "input": kwargs.get("input")[:MAX_LOG_MESSAGE_LENGTH],
        "api_key_last_four_digits": f"sk-{response.api_key[-4:]}",
        "response_time": ft.duration,
        "request.model": kwargs.get("model") or kwargs.get("engine"),
        "response.model": response.model,
        "response.usage.total_tokens": response.usage.total_tokens,
        "response.usage.prompt_tokens": response.usage.prompt_tokens,
        "response.headers.llmVersion": response_headers.get("openai-version"),
        "response.headers.ratelimitLimitRequests": check_rate_limit_header(response_headers, "x-ratelimit-limit-requests", True),
        "response.headers.ratelimitLimitTokens": check_rate_limit_header(response_headers, "x-ratelimit-limit-tokens", True),
        "response.headers.ratelimitResetTokens": check_rate_limit_header(response_headers, "x-ratelimit-reset-tokens", False),
        "response.headers.ratelimitResetRequests": check_rate_limit_header(response_headers, "x-ratelimit-reset-requests", False),
        "response.headers.ratelimitRemainingTokens": check_rate_limit_header(response_headers, "x-ratelimit-remaining-tokens", True),
        "response.headers.ratelimitRemainingRequests": check_rate_limit_header(response_headers, "x-ratelimit-remaining-requests", True),
        "response.api_type": response.api_type,
        "vendor": "openAI",
        "response.organization": response.organization,
        "api_version": response_headers.get("openai-version"),
    }

    transaction.record_ml_event("LlmEmbedding", embedding_dict)


def check_rate_limit_header(response_headers, header_name, is_int):
    if header_name in response_headers:
        header_value = response_headers.get(header_name)
        if is_int:
            header_value = int(header_value)
        return header_value
    else:
        return None


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
