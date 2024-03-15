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
import openai
import sys
import uuid

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

_logger = logging.getLogger(__name__)


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

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/embedding/OpenAI")
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

    completion_id = str(uuid.uuid4())
    request_message_list = kwargs.get("messages", [])

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/completion/OpenAI")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = wrapped(*args, **kwargs)
    except Exception as exc:
        _record_completion_error(transaction, linking_metadata, completion_id, kwargs, ft, exc)
        raise
    _handle_completion_success(transaction, linking_metadata, completion_id, kwargs, ft, return_val)
    return return_val


def check_rate_limit_header(response_headers, header_name, is_int):
    if not response_headers:
        return None

    if header_name in response_headers:
        header_value = response_headers.get(header_name)
        if is_int:
            try:
                header_value = int(header_value)
            except Exception:
                pass
        return header_value
    else:
        return None


def create_chat_completion_message_event(
    transaction,
    input_message_list,
    chat_completion_id,
    span_id,
    trace_id,
    response_model,
    request_model,
    response_id,
    request_id,
    llm_metadata,
    output_message_list,
):
    settings = transaction.settings if transaction.settings is not None else global_settings()

    # Loop through all input messages received from the create request and emit a custom event for each one
    for index, message in enumerate(input_message_list):
        message_content = message.get("content")

        # Response ID was set, append message index to it.
        if response_id:
            message_id = "%s-%d" % (response_id, index)
        # No response IDs, use random UUID
        else:
            message_id = str(uuid.uuid4())

        chat_completion_input_message_dict = {
            "id": message_id,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "token_count": settings.ai_monitoring.llm_token_count_callback(request_model, message_content)
            if settings.ai_monitoring.llm_token_count_callback
            else None,
            "transaction_id": transaction.guid,
            "role": message.get("role"),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": response_model,
            "vendor": "openai",
            "ingest_source": "Python",
        }

        if settings.ai_monitoring.record_content.enabled:
            chat_completion_input_message_dict["content"] = message_content

        chat_completion_input_message_dict.update(llm_metadata)

        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_input_message_dict)

    if output_message_list:
        # Loop through all output messages received from the LLM response and emit a custom event for each one
        for index, message in enumerate(output_message_list):
            message_content = message.get("content")

            # Add offset of input_message_length so we don't receive any duplicate index values that match the input message IDs
            index += len(input_message_list)

            # Response ID was set, append message index to it.
            if response_id:
                message_id = "%s-%d" % (response_id, index)
            # No response IDs, use random UUID
            else:
                message_id = str(uuid.uuid4())

            chat_completion_output_message_dict = {
                "id": message_id,
                "request_id": request_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "token_count": settings.ai_monitoring.llm_token_count_callback(response_model, message_content)
                if settings.ai_monitoring.llm_token_count_callback
                else None,
                "transaction_id": transaction.guid,
                "role": message.get("role"),
                "completion_id": chat_completion_id,
                "sequence": index,
                "response.model": response_model,
                "vendor": "openai",
                "ingest_source": "Python",
                "is_response": True,
            }

            if settings.ai_monitoring.record_content.enabled:
                chat_completion_output_message_dict["content"] = message_content

            chat_completion_output_message_dict.update(llm_metadata)

            transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_output_message_dict)


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

    # Obtain attributes to be stored on embedding events regardless of whether we hit an error
    embedding_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/embedding/OpenAI")
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


def _record_embedding_success(transaction, embedding_id, linking_metadata, kwargs, ft, response):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    response_headers = getattr(response, "_nr_response_headers", {})
    input = kwargs.get("input")

    # In v1, response objects are pydantic models so this function call converts the
    # object back to a dictionary for backwards compatibility.
    attribute_response = response
    if OPENAI_V1:
        attribute_response = response.model_dump()

    request_id = response_headers.get("x-request-id")
    response_model = attribute_response.get("model")
    response_usage = attribute_response.get("usage", {}) or {}
    organization = (
        response_headers.get("openai-organization") if OPENAI_V1 else getattr(attribute_response, "organization", None)
    )

    full_embedding_response_dict = {
        "id": embedding_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "token_count": settings.ai_monitoring.llm_token_count_callback(response_model, input)
        if settings.ai_monitoring.llm_token_count_callback
        else None,
        "request.model": kwargs.get("model") or kwargs.get("engine"),
        "request_id": request_id,
        "duration": ft.duration,
        "response.model": response_model,
        "response.organization": organization,
        "response.usage.total_tokens": response_usage.get("total_tokens"),
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens"),
        "response.headers.llmVersion": response_headers.get("openai-version"),
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
        "vendor": "openai",
        "ingest_source": "Python",
    }
    if settings.ai_monitoring.record_content.enabled:
        full_embedding_response_dict["input"] = input

    full_embedding_response_dict.update(_get_llm_attributes(transaction))
    transaction.record_custom_event("LlmEmbedding", full_embedding_response_dict)


def _record_embedding_error(transaction, embedding_id, linking_metadata, kwargs, ft, exc):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    model = kwargs.get("model") or kwargs.get("engine")
    input = kwargs.get("input")

    if OPENAI_V1:
        response = getattr(exc, "response", None)
        response_headers = getattr(response, "headers", None) or {}
        exc_organization = response_headers.get("openai-organization")
        # There appears to be a bug here in openai v1 where despite having code,
        # param, etc in the error response, they are not populated on the exception
        # object so grab them from the response body object instead.
        body = getattr(exc, "body", None) or {}
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "status_code", None),
            "error.message": body.get("message"),
            "error.code": body.get("code"),
            "error.param": body.get("param"),
            "embedding_id": embedding_id,
        }
    else:
        exc_organization = getattr(exc, "organization", None)
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "http_status", None),
            "error.message": getattr(exc, "_message", None),
            "error.code": getattr(getattr(exc, "error", None), "code", None),
            "error.param": getattr(exc, "param", None),
            "embedding_id": embedding_id,
        }
    message = notice_error_attributes.pop("error.message")
    if message:
        exc._nr_message = message
    ft.notice_error(
        attributes=notice_error_attributes,
    )
    # Exit the trace now so that the duration is calculated.
    ft.__exit__(*sys.exc_info())

    error_embedding_dict = {
        "id": embedding_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "token_count": settings.ai_monitoring.llm_token_count_callback(model, input)
        if settings.ai_monitoring.llm_token_count_callback
        else None,
        "request.model": model,
        "vendor": "openai",
        "ingest_source": "Python",
        "response.organization": exc_organization,
        "duration": ft.duration,
        "error": True,
    }
    if settings.ai_monitoring.record_content.enabled:
        error_embedding_dict["input"] = input

    error_embedding_dict.update(_get_llm_attributes(transaction))
    transaction.record_custom_event("LlmEmbedding", error_embedding_dict)


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

    completion_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/completion/OpenAI")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = await wrapped(*args, **kwargs)
    except Exception as exc:
        _record_completion_error(transaction, linking_metadata, completion_id, kwargs, ft, exc)
        raise

    _handle_completion_success(transaction, linking_metadata, completion_id, kwargs, ft, return_val)
    return return_val


def _handle_completion_success(transaction, linking_metadata, completion_id, kwargs, ft, return_val):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    request_message_list = kwargs.get("messages", [])
    stream = kwargs.get("stream", False)
    # Only if streaming and streaming monitoring is enabled and the response is not empty
    # do we not exit the function trace.
    if not stream or not settings.ai_monitoring.streaming.enabled or not return_val:
        ft.__exit__(None, None, None)

    # If the return value is empty or stream monitoring is disabled exit early.
    if not return_val or (stream and not settings.ai_monitoring.streaming.enabled):
        return

    if stream:
        # The function trace will be exited when in the final iteration of the response
        # generator.
        setattr(return_val, "_nr_ft", ft)
        setattr(return_val, "_nr_openai_attrs", getattr(return_val, "_nr_openai_attrs", {}))
        return_val._nr_openai_attrs["messages"] = kwargs.get("messages", [])
        return_val._nr_openai_attrs["temperature"] = kwargs.get("temperature")
        return_val._nr_openai_attrs["max_tokens"] = kwargs.get("max_tokens")
        return_val._nr_openai_attrs["model"] = kwargs.get("model") or kwargs.get("engine")
        return

    # If response is not a stream generator, record the event data.
    # At this point, we have a response so we can grab attributes only available on the response object
    response_headers = getattr(return_val, "_nr_response_headers", {})
    # In v1, response objects are pydantic models so this function call converts the
    # object back to a dictionary for backwards compatibility.
    response = return_val
    if OPENAI_V1:
        response = response.model_dump()

    _record_completion_success(transaction, linking_metadata, completion_id, kwargs, ft, response_headers, response)


def _record_completion_success(transaction, linking_metadata, completion_id, kwargs, ft, response_headers, response):
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    request_model = kwargs.get("model") or kwargs.get("engine")

    if response:
        response_model = response.get("model")
        response_id = response.get("id")
        response_usage = response.get("usage") or {}
        output_message_list = []
        finish_reason = None
        choices = response.get("choices") or []
        if choices:
            output_message_list = [choices[0].get("message")]
            finish_reason = choices[0].get("finish_reason")
    else:
        response_model = kwargs.get("response.model")
        response_id = kwargs.get("id")
        response_usage = {}
        output_message_list = []
        finish_reason = None
        if "content" in kwargs:
            output_message_list = [{"content": kwargs.get("content"), "role": kwargs.get("role")}]
            finish_reason = kwargs.get("finish_reason")

    request_id = response_headers.get("x-request-id")
    organization = response_headers.get("openai-organization") or getattr(response, "organization", None)
    messages = kwargs.get("messages", None) or []
    input_message_list = list(messages)
    full_chat_completion_summary_dict = {
        "id": completion_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "request.model": request_model,
        "request.temperature": kwargs.get("temperature"),
        "request.max_tokens": kwargs.get("max_tokens"),
        "vendor": "openai",
        "ingest_source": "Python",
        "request_id": request_id,
        "duration": ft.duration,
        "response.model": response_model,
        "response.organization": organization,
        "response.usage.completion_tokens": response_usage.get("completion_tokens"),
        "response.usage.total_tokens": response_usage.get("total_tokens"),
        "response.usage.prompt_tokens": response_usage.get("prompt_tokens"),
        "response.choices.finish_reason": finish_reason,
        "response.headers.llmVersion": response_headers.get("openai-version"),
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
        "response.number_of_messages": len(input_message_list) + len(output_message_list),
    }
    llm_metadata = _get_llm_attributes(transaction)
    full_chat_completion_summary_dict.update(llm_metadata)
    transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)

    create_chat_completion_message_event(
        transaction,
        input_message_list,
        completion_id,
        span_id,
        trace_id,
        response_model,
        request_model,
        response_id,
        request_id,
        llm_metadata,
        output_message_list,
    )


def _record_completion_error(transaction, linking_metadata, completion_id, kwargs, ft, exc):
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    request_message_list = kwargs.get("messages", None) or []
    request_model = kwargs.get("model") or kwargs.get("engine")
    if OPENAI_V1:
        response = getattr(exc, "response", None)
        response_headers = getattr(response, "headers", None) or {}
        exc_organization = response_headers.get("openai-organization")
        # There appears to be a bug here in openai v1 where despite having code,
        # param, etc in the error response, they are not populated on the exception
        # object so grab them from the response body object instead.
        body = getattr(exc, "body", None) or {}
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "status_code", None),
            "error.message": body.get("message"),
            "error.code": body.get("code"),
            "error.param": body.get("param"),
            "completion_id": completion_id,
        }
    else:
        exc_organization = getattr(exc, "organization", None)
        notice_error_attributes = {
            "http.statusCode": getattr(exc, "http_status", None),
            "error.message": getattr(exc, "_message", None),
            "error.code": getattr(getattr(exc, "error", None), "code", None),
            "error.param": getattr(exc, "param", None),
            "completion_id": completion_id,
        }
    # Override the default message if it is not empty.
    message = notice_error_attributes.pop("error.message")
    if message:
        exc._nr_message = message

    ft.notice_error(
        attributes=notice_error_attributes,
    )
    # Stop the span now so we compute the duration before we create the events.
    ft.__exit__(*sys.exc_info())

    # In a rare case where we are streaming the response and we do get back a request
    # and response id, even though an error was encountered, record them.
    response_headers = kwargs.get("response_headers") or {}
    request_id = response_headers.get("x-request-id")
    response_id = kwargs.get("id")
    error_chat_completion_dict = {
        "id": completion_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction.guid,
        "response.number_of_messages": len(request_message_list),
        "request.model": request_model,
        "request.temperature": kwargs.get("temperature"),
        "request.max_tokens": kwargs.get("max_tokens"),
        "vendor": "openai",
        "ingest_source": "Python",
        "response.organization": exc_organization,
        "duration": ft.duration,
        "error": True,
    }
    llm_metadata = _get_llm_attributes(transaction)
    error_chat_completion_dict.update(llm_metadata)
    transaction.record_custom_event("LlmChatCompletionSummary", error_chat_completion_dict)

    output_message_list = []
    if "content" in kwargs:
        output_message_list = [{"content": kwargs.get("content"), "role": kwargs.get("role")}]

    create_chat_completion_message_event(
        transaction,
        request_message_list,
        completion_id,
        span_id,
        trace_id,
        kwargs.get("response.model"),
        request_model,
        response_id,
        request_id,
        llm_metadata,
        output_message_list,
    )


def wrap_convert_to_openai_object(wrapped, instance, args, kwargs):
    """Obtain reponse headers for v0."""
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
    nr_response_headers = getattr(response, "headers", None) or {}
    return nr_response_headers


def wrap_base_client_process_response_sync(wrapped, instance, args, kwargs):
    """Obtain response headers for v1."""
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    nr_response_headers = bind_base_client_process_response(*args, **kwargs)
    return_val = wrapped(*args, **kwargs)
    return_val._nr_response_headers = nr_response_headers
    return return_val


async def wrap_base_client_process_response_async(wrapped, instance, args, kwargs):
    """Obtain response headers for v1."""
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    nr_response_headers = bind_base_client_process_response(*args, **kwargs)
    return_val = await wrapped(*args, **kwargs)
    return_val._nr_response_headers = nr_response_headers
    return return_val


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
            _record_stream_chunk(self, return_val)
        except StopIteration as e:
            _record_events_on_stop_iteration(self, transaction)
            raise
        except Exception as exc:
            _handle_streaming_completion_error(self, transaction, exc)
            raise
        return return_val

    def close(self):
        return super(GeneratorProxy, self).close()


def _record_stream_chunk(self, return_val):
    if return_val:
        if OPENAI_V1:
            if getattr(return_val, "data", "").startswith("[DONE]"):
                return
            return_val = return_val.json()
            self._nr_openai_attrs["response_headers"] = getattr(self, "_nr_response_headers", {})
        else:
            self._nr_openai_attrs["response_headers"] = getattr(return_val, "_nr_response_headers", {})
        choices = return_val.get("choices") or []
        self._nr_openai_attrs["response.model"] = return_val.get("model")
        self._nr_openai_attrs["id"] = return_val.get("id")
        self._nr_openai_attrs["response.organization"] = return_val.get("organization")
        if choices:
            delta = choices[0].get("delta") or {}
            if delta:
                self._nr_openai_attrs["content"] = self._nr_openai_attrs.get("content", "") + (
                    delta.get("content") or ""
                )
                self._nr_openai_attrs["role"] = self._nr_openai_attrs.get("role") or delta.get("role")
            self._nr_openai_attrs["finish_reason"] = choices[0].get("finish_reason")


def _record_events_on_stop_iteration(self, transaction):
    if hasattr(self, "_nr_ft"):
        openai_attrs = getattr(self, "_nr_openai_attrs", {})
        self._nr_ft.__exit__(None, None, None)

        # If there are no openai attrs exit early as there's no data to record.
        if not openai_attrs:
            return

        completion_id = str(uuid.uuid4())
        linking_metadata = get_trace_linking_metadata()
        response_headers = openai_attrs.get("response_headers") or {}
        _record_completion_success(
            transaction, linking_metadata, completion_id, openai_attrs, self._nr_ft, response_headers, None
        )
        # Clear cached data as this can be very large.
        # Note this is also important for not reporting the events twice. In openai v1
        # there are two loops around the iterator, the second is meant to clear the
        # stream since there is a condition where the iterator may exit before all the
        # stream contents is read. This results in StopIteration being raised twice
        # instead of once at the end of the loop.
        self._nr_openai_attrs = {}


def _handle_streaming_completion_error(self, transaction, exc):
    if hasattr(self, "_nr_ft"):
        openai_attrs = getattr(self, "_nr_openai_attrs", {})

        # If there are no openai attrs exit early as there's no data to record.
        if not openai_attrs:
            self._nr_ft.__exit__(*sys.exc_info())
            return
        linking_metadata = get_trace_linking_metadata()
        completion_id = str(uuid.uuid4())
        _record_completion_error(transaction, linking_metadata, completion_id, openai_attrs, self._nr_ft, exc)


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
            _record_stream_chunk(self, return_val)
        except StopAsyncIteration as e:
            _record_events_on_stop_iteration(self, transaction)
            raise
        except Exception as exc:
            _handle_streaming_completion_error(self, transaction, exc)
            raise
        return return_val

    async def aclose(self):
        return await super(AsyncGeneratorProxy, self).aclose()


def wrap_stream_iter_events_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled or not settings.ai_monitoring.streaming.enabled:
        return wrapped(*args, **kwargs)

    return_val = wrapped(*args, **kwargs)
    proxied_return_val = GeneratorProxy(return_val)
    set_attrs_on_generator_proxy(proxied_return_val, instance)
    return proxied_return_val


def wrap_stream_iter_events_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled or not settings.ai_monitoring.streaming.enabled:
        return wrapped(*args, **kwargs)

    return_val = wrapped(*args, **kwargs)
    proxied_return_val = AsyncGeneratorProxy(return_val)
    set_attrs_on_generator_proxy(proxied_return_val, instance)
    return proxied_return_val


def set_attrs_on_generator_proxy(proxy, instance):
    """Pass the nr attributes to the generator proxy."""
    proxy._nr_ft = instance._nr_ft
    proxy._nr_response_headers = instance._nr_response_headers
    proxy._nr_openai_attrs = instance._nr_openai_attrs


def wrap_engine_api_resource_create_sync(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    stream = is_stream(wrapped, args, kwargs)
    return_val = wrapped(*args, **kwargs)
    if stream and settings.ai_monitoring.streaming.enabled:
        return GeneratorProxy(return_val)
    else:
        return return_val


async def wrap_engine_api_resource_create_async(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    stream = is_stream(wrapped, args, kwargs)
    return_val = await wrapped(*args, **kwargs)
    if stream and settings.ai_monitoring.streaming.enabled:
        return AsyncGeneratorProxy(return_val)
    else:
        return return_val


def is_stream(wrapped, args, kwargs):
    bound_args = bind_args(wrapped, args, kwargs)
    return bound_args["params"].get("stream", False)


def _get_llm_attributes(transaction):
    """Returns llm.* custom attributes off of the transaction."""
    custom_attrs_dict = transaction._custom_params
    llm_metadata = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}
    return llm_metadata


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


def instrument_openai_util(module):
    if hasattr(module, "convert_to_openai_object"):
        wrap_function_wrapper(module, "convert_to_openai_object", wrap_convert_to_openai_object)
        # This is to mark where we instrument so the SDK knows not to instrument them
        # again.
        setattr(module.convert_to_openai_object, "_nr_wrapped", True)


def instrument_openai_base_client(module):
    if hasattr(module, "BaseClient") and hasattr(module.BaseClient, "_process_response"):
        wrap_function_wrapper(module, "BaseClient._process_response", wrap_base_client_process_response_sync)
    else:
        if hasattr(module, "SyncAPIClient") and hasattr(module.SyncAPIClient, "_process_response"):
            wrap_function_wrapper(module, "SyncAPIClient._process_response", wrap_base_client_process_response_sync)
        if hasattr(module, "AsyncAPIClient") and hasattr(module.AsyncAPIClient, "_process_response"):
            wrap_function_wrapper(module, "AsyncAPIClient._process_response", wrap_base_client_process_response_async)


def instrument_openai_api_resources_abstract_engine_api_resource(module):
    if hasattr(module, "EngineAPIResource"):
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
