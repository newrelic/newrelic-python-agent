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
from newrelic.common.llm_utils import AsyncLLMStreamProxy, LLMStreamProxy
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

ANTHROPIC_VERSION = get_package_version("anthropic")
EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE = (
    "Exception occurred in Anthropic instrumentation: While reporting an exception "
    "in Anthropic, another exception occurred. Report this issue to New Relic "
    "Support."
)
RECORD_EVENTS_FAILURE_LOG_MESSAGE = (
    "Exception occurred in Anthropic instrumentation: Failed to record LLM events. "
    "Please report this issue to New Relic Support."
)
STREAM_PARSING_FAILURE_LOG_MESSAGE = "Exception occurred in Anthropic instrumentation: Failed to process event stream information. Please report this issue to New Relic Support."

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

    # Streaming path: return_val is Stream[RawMessageStreamEvent]
    if kwargs.get("stream"):
        try:
            streaming_events = []
            proxied = NRMessageStreamProxy(
                return_val,
                on_stream_chunk=_handle_stream_chunk(
                    streaming_events=streaming_events, request_timestamp=request_timestamp
                ),
                on_stop_iteration=_handle_streaming_create_success(
                    linking_metadata=linking_metadata,
                    completion_id=completion_id,
                    kwargs=kwargs,
                    ft=ft,
                    streaming_events=streaming_events,
                    request_timestamp=request_timestamp,
                    transaction=transaction,
                ),
                on_error=_handle_streaming_create_error(
                    linking_metadata=linking_metadata,
                    completion_id=completion_id,
                    kwargs=kwargs,
                    ft=ft,
                    request_timestamp=request_timestamp,
                ),
            )
            proxied._nr_ft = ft
            proxied._nr_metadata = linking_metadata
            return proxied
        except Exception:
            ft.__exit__(*sys.exc_info())
            return return_val

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

    # Streaming path: return_val is AsyncStream[RawMessageStreamEvent]
    if kwargs.get("stream"):
        try:
            streaming_events = []
            proxied = NRAsyncMessageStreamProxy(
                return_val,
                on_stream_chunk=_handle_stream_chunk(
                    streaming_events=streaming_events, request_timestamp=request_timestamp
                ),
                on_stop_iteration=_handle_streaming_create_success(
                    linking_metadata=linking_metadata,
                    completion_id=completion_id,
                    kwargs=kwargs,
                    ft=ft,
                    streaming_events=streaming_events,
                    request_timestamp=request_timestamp,
                    transaction=transaction,
                ),
                on_error=_handle_streaming_create_error(
                    linking_metadata=linking_metadata,
                    completion_id=completion_id,
                    kwargs=kwargs,
                    ft=ft,
                    request_timestamp=request_timestamp,
                ),
            )
            proxied._nr_ft = ft
            proxied._nr_metadata = linking_metadata
            return proxied
        except Exception:
            ft.__exit__(*sys.exc_info())
            return return_val

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


def _handle_stream_chunk(*, streaming_events, request_timestamp):
    def _on_stream_chunk(self, chunk):
        streaming_events.append(chunk)
        # Track time to first text token
        if not hasattr(self, "_nr_time_to_first_token") and request_timestamp:
            chunk_type = getattr(chunk, "type", None)
            if chunk_type == "content_block_delta":
                delta = getattr(chunk, "delta", None)
                if getattr(delta, "type", None) == "text_delta":
                    self._nr_time_to_first_token = int(1000.0 * time.time()) - request_timestamp

    return _on_stream_chunk


def _handle_streaming_create_success(
    *, linking_metadata, completion_id, kwargs, ft, streaming_events, request_timestamp, transaction
):
    def _on_stop_iteration(self, transaction):
        if hasattr(self, "_nr_ft"):
            linking_metadata_used = self._nr_metadata or get_trace_linking_metadata()
            self._nr_ft.__exit__(None, None, None)
            active_ft = self._nr_ft
        else:
            linking_metadata_used = linking_metadata
            ft.__exit__(None, None, None)
            active_ft = ft

        try:
            # Reconstruct response data from accumulated raw SSE events
            response_id = None
            response_model = None
            input_tokens = None
            output_tokens = None
            stop_reason = None
            text_parts = []

            for chunk in streaming_events:
                chunk_type = getattr(chunk, "type", None)
                if chunk_type == "message_start":
                    msg = getattr(chunk, "message", None)
                    response_id = getattr(msg, "id", None)
                    response_model = getattr(msg, "model", None)
                    usage = getattr(msg, "usage", None)
                    input_tokens = getattr(usage, "input_tokens", None)
                elif chunk_type == "content_block_delta":
                    delta = getattr(chunk, "delta", None)
                    if getattr(delta, "type", None) == "text_delta":
                        text_parts.append(getattr(delta, "text", ""))
                elif chunk_type == "message_delta":
                    delta = getattr(chunk, "delta", None)
                    stop_reason = getattr(delta, "stop_reason", None)
                    usage = getattr(chunk, "usage", None)
                    output_tokens = getattr(usage, "output_tokens", None)

            # Pass the accumulated text directly; create_chat_completion_message_event handles strings.
            response_content = "".join(text_parts) if text_parts else None

            _record_completion_success(
                transaction=transaction,
                linking_metadata=linking_metadata_used,
                completion_id=completion_id,
                kwargs=kwargs,
                ft=active_ft,
                response_id=response_id,
                response_model=response_model,
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response_content=response_content,
                request_timestamp=request_timestamp,
                time_to_first_token=getattr(self, "_nr_time_to_first_token", None),
            )
        except Exception:
            _logger.warning(STREAM_PARSING_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            streaming_events.clear()

    return _on_stop_iteration


def _handle_streaming_create_error(*, linking_metadata, completion_id, kwargs, ft, request_timestamp):
    def _on_error(self, transaction):
        exc = sys.exc_info()[1]
        _record_completion_error(
            transaction=transaction,
            linking_metadata=self._nr_metadata if hasattr(self, "_nr_metadata") else linking_metadata,
            completion_id=completion_id,
            kwargs=kwargs,
            ft=self._nr_ft if hasattr(self, "_nr_ft") else ft,
            exc=exc,
            request_timestamp=request_timestamp,
        )

    return _on_error


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

        # TODO: Complete token counting
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


def wrap_messages_stream(manager_cls):
    def _wrap_messages_stream(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        settings = transaction.settings or global_settings()
        if not settings.ai_monitoring.enabled:
            return wrapped(*args, **kwargs)

        # Framework metric also used for entity tagging in the UI
        transaction.add_ml_model_info("Anthropic", ANTHROPIC_VERSION)
        transaction._add_agent_attribute("llm", True)

        try:
            return_val = wrapped(*args, **kwargs)
        except Exception as exc:
            try:
                completion_id = str(uuid.uuid4())
                request_timestamp = int(1000.0 * time.time())

                # When an exception is thrown while creating the MessageStreamManager, we won't have another chance to
                # capture any of the relevant data. To ensure we at least report something useful, capture the attempt
                # to call stream here as a FunctionTrace and report the exception on it.
                ft = FunctionTrace(name="stream", group="Llm/completion/Anthropic")
                ft.__enter__()
                linking_metadata = get_trace_linking_metadata()

                _record_completion_error(
                    transaction=transaction,
                    linking_metadata=linking_metadata,
                    completion_id=completion_id,
                    kwargs=kwargs,
                    ft=ft,
                    exc=exc,
                    request_timestamp=request_timestamp,
                )
            except Exception:
                _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE, exc_info=True)

            # Always reraise the exception
            raise

        return manager_cls(return_val, transaction, kwargs)

    return _wrap_messages_stream


class NRMessageStreamProxy(LLMStreamProxy):
    def __enter__(self):
        return self

    def __stream__(self):
        generator = self.__wrapped__.__stream__()
        proxied_generator = NRMessageStreamProxy(
            generator,
            on_stream_chunk=self._nr_on_stream_chunk,
            on_stop_iteration=self._nr_on_stop_iteration,
            on_error=self._nr_on_error,
        )
        for item in proxied_generator:  # noqa: UP028
            yield item

    @property
    def text_stream(self):
        return self.__stream_text__()

    def __stream_text__(self):
        for text in self.__wrapped__.__stream_text__():
            if not hasattr(self, "_nr_time_to_first_token") and hasattr(self, "_nr_request_timestamp"):
                self._nr_time_to_first_token = int(1000.0 * time.time()) - self._nr_request_timestamp
            yield text


class NRAsyncMessageStreamProxy(AsyncLLMStreamProxy):
    async def __aenter__(self):
        return self

    async def __stream__(self):
        generator = self.__wrapped__.__stream__()
        proxied_generator = NRAsyncMessageStreamProxy(
            generator,
            on_stream_chunk=self._nr_on_stream_chunk,
            on_stop_iteration=self._nr_on_stop_iteration,
            on_error=self._nr_on_error,
        )
        async for item in proxied_generator:
            yield item

    @property
    def text_stream(self):
        return self.__stream_text__()

    async def __stream_text__(self):
        async for text in self.__wrapped__.__stream_text__():
            if not hasattr(self, "_nr_time_to_first_token") and hasattr(self, "_nr_request_timestamp"):
                self._nr_time_to_first_token = int(1000.0 * time.time()) - self._nr_request_timestamp
            yield text


class NRMessageStreamManager(ObjectProxy):
    def __init__(self, wrappped, transaction, kwargs):
        super().__init__(wrappped)
        self._nr_transaction = transaction
        self._nr_kwargs = kwargs
        self._nr_ft = None
        self._nr_proxy = None
        self._nr_message_stream = None
        self._nr_events_recorded = False
        self._nr_completion_id = str(uuid.uuid4())
        self._nr_request_timestamp = int(1000.0 * time.time())
        self._nr_streaming_events = []
        self._nr_linking_metadata = None

    def __enter__(self):
        ft = self._nr_ft = FunctionTrace(name="stream", group="Llm/completion/Anthropic")
        ft.__enter__()
        self._nr_linking_metadata = get_trace_linking_metadata()

        try:
            message_stream = self._nr_message_stream = self.__wrapped__.__enter__()
        except Exception as exc:
            _record_completion_error(
                transaction=self._nr_transaction,
                linking_metadata=self._nr_linking_metadata,
                completion_id=self._nr_completion_id,
                kwargs=self._nr_kwargs,
                ft=ft,
                exc=exc,
                request_timestamp=self._nr_request_timestamp,
            )
            self._nr_events_recorded = True
            raise

        # Wrap the MessageStream with NRMessageStreamProxy for time_to_first_token tracking.
        # on_stream_chunk receives ParsedMessageStreamEvent objects (same raw events as create(stream=True)).
        # on_stop_iteration fires when the user exhausts the proxy via __next__().
        # If the user uses stream.text_stream instead, on_stop_iteration is bypassed and
        # __exit__ handles event recording as a fallback.
        proxied_stream = self._nr_proxy = NRMessageStreamProxy(
            message_stream,
            on_stream_chunk=_handle_stream_chunk(
                streaming_events=self._nr_streaming_events, request_timestamp=self._nr_request_timestamp
            ),
            on_stop_iteration=_handle_stream_manager_success(self),
            on_error=_handle_stream_manager_error(self),
        )
        proxied_stream._nr_ft = self._nr_ft
        proxied_stream._nr_metadata = self._nr_linking_metadata
        proxied_stream._nr_request_timestamp = self._nr_request_timestamp
        return proxied_stream

    def __exit__(self, exc_type, exc, exc_tb):
        # Fallback: record events if not already recorded (e.g., user used text_stream).
        if not self._nr_events_recorded:
            if exc_type is None:
                snapshot = getattr(self._nr_message_stream, "_MessageStream__final_message_snapshot", None)
                if snapshot:
                    usage = getattr(snapshot, "usage", None)
                    content = getattr(snapshot, "content", None)
                    response_content = (
                        " ".join(block.text for block in content if getattr(block, "type", None) == "text")
                        if content
                        else None
                    )
                    _record_completion_success(
                        transaction=self._nr_transaction,
                        linking_metadata=self._nr_linking_metadata,
                        completion_id=self._nr_completion_id,
                        kwargs=self._nr_kwargs,
                        ft=self._nr_ft,
                        response_id=getattr(snapshot, "id", None),
                        response_model=getattr(snapshot, "model", None),
                        stop_reason=getattr(snapshot, "stop_reason", None),
                        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
                        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
                        response_content=response_content,
                        request_timestamp=self._nr_request_timestamp,
                        time_to_first_token=getattr(self._nr_proxy, "_nr_time_to_first_token", None),
                    )
                self._nr_ft.__exit__(None, None, None)
            else:
                _record_completion_error(
                    transaction=self._nr_transaction,
                    linking_metadata=self._nr_linking_metadata,
                    completion_id=self._nr_completion_id,
                    kwargs=self._nr_kwargs,
                    ft=self._nr_ft,
                    exc=exc,
                    request_timestamp=self._nr_request_timestamp,
                )
            self._nr_events_recorded = True
        self.__wrapped__.__exit__(exc_type, exc, exc_tb)


class NRAsyncMessageStreamManager(ObjectProxy):
    def __init__(self, wrappped, transaction, kwargs):
        super().__init__(wrappped)
        self._nr_transaction = transaction
        self._nr_kwargs = kwargs
        self._nr_ft = None
        self._nr_proxy = None
        self._nr_message_stream = None
        self._nr_events_recorded = False
        self._nr_completion_id = str(uuid.uuid4())
        self._nr_request_timestamp = int(1000.0 * time.time())
        self._nr_streaming_events = []
        self._nr_linking_metadata = None

    async def __aenter__(self):
        ft = self._nr_ft = FunctionTrace(name="stream", group="Llm/completion/Anthropic")
        ft.__enter__()
        self._nr_linking_metadata = get_trace_linking_metadata()

        try:
            message_stream = self._nr_message_stream = await self.__wrapped__.__aenter__()
        except Exception as exc:
            _record_completion_error(
                transaction=self._nr_transaction,
                linking_metadata=self._nr_linking_metadata,
                completion_id=self._nr_completion_id,
                kwargs=self._nr_kwargs,
                ft=ft,
                exc=exc,
                request_timestamp=self._nr_request_timestamp,
            )
            self._nr_events_recorded = True
            raise

        # Wrap the MessageStream with NRAsyncMessageStreamProxy for time_to_first_token tracking.
        # on_stream_chunk receives ParsedMessageStreamEvent objects (same raw events as create(stream=True)).
        # on_stop_iteration fires when the user exhausts the proxy via __next__().
        # If the user uses stream.text_stream instead, on_stop_iteration is bypassed and
        # __exit__ handles event recording as a fallback.
        proxied_stream = self._nr_proxy = NRAsyncMessageStreamProxy(
            message_stream,
            on_stream_chunk=_handle_stream_chunk(
                streaming_events=self._nr_streaming_events, request_timestamp=self._nr_request_timestamp
            ),
            on_stop_iteration=_handle_stream_manager_success(self),
            on_error=_handle_stream_manager_error(self),
        )
        proxied_stream._nr_ft = self._nr_ft
        proxied_stream._nr_metadata = self._nr_linking_metadata
        proxied_stream._nr_request_timestamp = self._nr_request_timestamp
        return proxied_stream

    async def __aexit__(self, exc_type, exc, exc_tb):
        # Fallback: record events if not already recorded (e.g., user used text_stream).
        if not self._nr_events_recorded:
            if exc_type is None:
                snapshot = getattr(self._nr_message_stream, "_AsyncMessageStream__final_message_snapshot", None)
                if snapshot:
                    usage = getattr(snapshot, "usage", None)
                    content = getattr(snapshot, "content", None)
                    response_content = (
                        " ".join(block.text for block in content if getattr(block, "type", None) == "text")
                        if content
                        else None
                    )
                    _record_completion_success(
                        transaction=self._nr_transaction,
                        linking_metadata=self._nr_linking_metadata,
                        completion_id=self._nr_completion_id,
                        kwargs=self._nr_kwargs,
                        ft=self._nr_ft,
                        response_id=getattr(snapshot, "id", None),
                        response_model=getattr(snapshot, "model", None),
                        stop_reason=getattr(snapshot, "stop_reason", None),
                        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
                        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
                        response_content=response_content,
                        request_timestamp=self._nr_request_timestamp,
                        time_to_first_token=getattr(self._nr_proxy, "_nr_time_to_first_token", None),
                    )
                self._nr_ft.__exit__(None, None, None)
            else:
                _record_completion_error(
                    transaction=self._nr_transaction,
                    linking_metadata=self._nr_linking_metadata,
                    completion_id=self._nr_completion_id,
                    kwargs=self._nr_kwargs,
                    ft=self._nr_ft,
                    exc=exc,
                    request_timestamp=self._nr_request_timestamp,
                )
            self._nr_events_recorded = True
        await self.__wrapped__.__aexit__(exc_type, exc, exc_tb)


def _handle_stream_manager_success(manager):
    """Returns on_stop_iteration callback for the stream() path.

    Fires when the user exhausts the proxy via iteration (__next__/__anext__).
    Uses MessageStream's accumulated snapshot for response data.
    """

    def _on_stop_iteration(self, transaction):
        if manager._nr_events_recorded:
            return
        manager._nr_events_recorded = True

        if hasattr(self, "_nr_ft"):
            linking_metadata_used = self._nr_metadata or get_trace_linking_metadata()
            self._nr_ft.__exit__(None, None, None)
        else:
            linking_metadata_used = manager._nr_linking_metadata or get_trace_linking_metadata()
            if manager._nr_ft:
                manager._nr_ft.__exit__(None, None, None)

        try:
            # Use MessageStream's accumulated snapshot for response data.
            # The private attribute is accessed directly to avoid the assert in current_message_snapshot.
            snapshot = getattr(manager._nr_message_stream, "_MessageStream__final_message_snapshot", None)
            if not snapshot:
                # Try AsyncMessageStream mangling if sync wasn't found
                snapshot = getattr(manager._nr_message_stream, "_AsyncMessageStream__final_message_snapshot", None)

            if snapshot:
                usage = getattr(snapshot, "usage", None)
                content = getattr(snapshot, "content", None)
                response_content = (
                    " ".join(block.text for block in content if getattr(block, "type", None) == "text")
                    if content
                    else None
                )
                _record_completion_success(
                    transaction=transaction,
                    linking_metadata=linking_metadata_used,
                    completion_id=manager._nr_completion_id,
                    kwargs=manager._nr_kwargs,
                    ft=manager._nr_ft,
                    response_id=getattr(snapshot, "id", None),
                    response_model=getattr(snapshot, "model", None),
                    stop_reason=getattr(snapshot, "stop_reason", None),
                    input_tokens=getattr(usage, "input_tokens", None) if usage else None,
                    output_tokens=getattr(usage, "output_tokens", None) if usage else None,
                    response_content=response_content,
                    request_timestamp=manager._nr_request_timestamp,
                    time_to_first_token=getattr(self, "_nr_time_to_first_token", None),
                )
        except Exception:
            _logger.warning(STREAM_PARSING_FAILURE_LOG_MESSAGE, exc_info=True)
        finally:
            manager._nr_streaming_events.clear()

    return _on_stop_iteration


def _handle_stream_manager_error(manager):
    """Returns on_error callback for the stream() path."""

    def _on_error(self, transaction):
        if manager._nr_events_recorded:
            return
        manager._nr_events_recorded = True

        exc = sys.exc_info()[1]
        _record_completion_error(
            transaction=transaction,
            linking_metadata=self._nr_metadata if hasattr(self, "_nr_metadata") else manager._nr_linking_metadata,
            completion_id=manager._nr_completion_id,
            kwargs=manager._nr_kwargs,
            ft=self._nr_ft if hasattr(self, "_nr_ft") else manager._nr_ft,
            exc=exc,
            request_timestamp=manager._nr_request_timestamp,
        )

    return _on_error


def instrument_anthropic_messages(module):
    if hasattr(module, "Messages"):
        wrap_function_wrapper(module, "Messages.create", wrap_messages_create_sync)
        wrap_function_wrapper(module, "Messages.stream", wrap_messages_stream(NRMessageStreamManager))

    if hasattr(module, "AsyncMessages"):
        wrap_function_wrapper(module, "AsyncMessages.create", wrap_messages_create_async)
        wrap_function_wrapper(module, "AsyncMessages.stream", wrap_messages_stream(NRAsyncMessageStreamManager))
