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
import re
import sys
import traceback
import uuid
from io import BytesIO

from botocore.response import StreamingBody

from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import message_trace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import (
    ObjectProxy,
    function_wrapper,
    wrap_function_wrapper,
)
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

QUEUE_URL_PATTERN = re.compile(r"https://sqs.([\w\d-]+).amazonaws.com/(\d+)/([^/]+)")
BOTOCORE_VERSION = get_package_version("botocore")


_logger = logging.getLogger(__name__)

EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE = "Exception occurred in botocore instrumentation for AWS Bedrock: While reporting an exception in botocore, another exception occurred. Report this issue to New Relic Support.\n%s"
REQUEST_EXTACTOR_FAILURE_LOG_MESSAGE = "Exception occurred in botocore instrumentation for AWS Bedrock: Failed to extract request information. Report this issue to New Relic Support.\n%s"
RESPONSE_EXTRACTOR_FAILURE_LOG_MESSAGE = "Exception occurred in botocore instrumentation for AWS Bedrock: Failed to extract response information. If the issue persists, report this issue to New Relic support.\n%s"
RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE = "Exception occurred in botocore instrumentation for AWS Bedrock: Failed to report response data. Report this issue to New Relic Support.\n%s"
EMBEDDING_STREAMING_UNSUPPORTED_LOG_MESSAGE = "Response streaming with embedding models is unsupported in botocore instrumentation for AWS Bedrock. If this feature is now supported by AWS and botocore, report this issue to New Relic Support."

UNSUPPORTED_MODEL_WARNING_SENT = False


def extract_sqs(*args, **kwargs):
    queue_value = kwargs.get("QueueUrl", "Unknown")
    return queue_value.rsplit("/", 1)[-1]


def extract_agent_attrs(*args, **kwargs):
    # Try to capture AWS SQS info as agent attributes. Log any exception to debug.
    agent_attrs = {}
    try:
        queue_url = kwargs.get("QueueUrl")
        if queue_url:
            m = QUEUE_URL_PATTERN.match(queue_url)
            if m:
                agent_attrs["messaging.system"] = "aws_sqs"
                agent_attrs["cloud.region"] = m.group(1)
                agent_attrs["cloud.account.id"] = m.group(2)
                agent_attrs["messaging.destination.name"] = m.group(3)
    except Exception as e:
        _logger.debug("Failed to capture AWS SQS info.", exc_info=True)
    return agent_attrs


def extract(argument_names, default=None):
    def extractor_list(*args, **kwargs):
        for argument_name in argument_names:
            argument_value = kwargs.get(argument_name)
            if argument_value:
                return argument_value
        return default

    def extractor_string(*args, **kwargs):
        return kwargs.get(argument_names, default)

    if isinstance(argument_names, str):
        return extractor_string

    return extractor_list


def bedrock_error_attributes(exception, bedrock_attrs):
    response = getattr(exception, "response", None)
    if not response:
        return bedrock_attrs

    response_metadata = response.get("ResponseMetadata", {})
    response_error = response.get("Error", {})
    bedrock_attrs.update(
        {
            "request_id": response_metadata.get("RequestId"),
            "http.statusCode": response_metadata.get("HTTPStatusCode"),
            "error.message": response_error.get("Message"),
            "error.code": response_error.get("Code"),
            "error": True,
        }
    )
    return bedrock_attrs


def create_chat_completion_message_event(
    transaction,
    input_message_list,
    output_message_list,
    chat_completion_id,
    span_id,
    trace_id,
    request_model,
    request_id,
    llm_metadata_dict,
    response_id=None,
):
    if not transaction:
        return

    settings = transaction.settings if transaction.settings is not None else global_settings()

    for index, message in enumerate(input_message_list):
        content = message.get("content", "")

        if response_id:
            id_ = "%s-%d" % (response_id, index)  # Response ID was set, append message index to it.
        else:
            id_ = str(uuid.uuid4())  # No response IDs, use random UUID

        chat_completion_message_dict = {
            "id": id_,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "token_count": (
                settings.ai_monitoring.llm_token_count_callback(request_model, content)
                if settings.ai_monitoring.llm_token_count_callback
                else None
            ),
            "role": message.get("role"),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": request_model,
            "vendor": "bedrock",
            "ingest_source": "Python",
        }

        if settings.ai_monitoring.record_content.enabled:
            chat_completion_message_dict["content"] = content

        chat_completion_message_dict.update(llm_metadata_dict)

        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_message_dict)

    for index, message in enumerate(output_message_list):
        index += len(input_message_list)
        content = message.get("content", "")
        # For anthropic models run via langchain, a list is returned with a dictionary of content inside
        # We only want to report the raw dictionary in the LLM message event
        if isinstance(content, list) and len(content) == 1:
            content = content[0]

        if response_id:
            id_ = "%s-%d" % (response_id, index)  # Response ID was set, append message index to it.
        else:
            id_ = str(uuid.uuid4())  # No response IDs, use random UUID

        chat_completion_message_dict = {
            "id": id_,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "token_count": (
                settings.ai_monitoring.llm_token_count_callback(request_model, content)
                if settings.ai_monitoring.llm_token_count_callback
                else None
            ),
            "role": message.get("role"),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": request_model,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "is_response": True,
        }

        if settings.ai_monitoring.record_content.enabled:
            chat_completion_message_dict["content"] = content

        chat_completion_message_dict.update(llm_metadata_dict)

        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_message_dict)


def extract_bedrock_titan_text_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)
    request_config = request_body.get("textGenerationConfig", {})

    input_message_list = [{"role": "user", "content": request_body.get("inputText")}]

    bedrock_attrs["input_message_list"] = input_message_list
    bedrock_attrs["request.max_tokens"] = request_config.get("maxTokenCount")
    bedrock_attrs["request.temperature"] = request_config.get("temperature")

    return bedrock_attrs


def extract_bedrock_mistral_text_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)
    bedrock_attrs["input_message_list"] = [{"role": "user", "content": request_body.get("prompt")}]
    bedrock_attrs["request.max_tokens"] = request_body.get("max_tokens")
    bedrock_attrs["request.temperature"] = request_body.get("temperature")
    return bedrock_attrs


def extract_bedrock_titan_text_model_response(response_body, bedrock_attrs):
    if response_body:
        response_body = json.loads(response_body)

        output_message_list = [
            {"role": "assistant", "content": result["outputText"]} for result in response_body.get("results", [])
        ]

        bedrock_attrs["response.choices.finish_reason"] = response_body["results"][0]["completionReason"]
        bedrock_attrs["output_message_list"] = output_message_list

    return bedrock_attrs


def extract_bedrock_mistral_text_model_response(response_body, bedrock_attrs):
    if response_body:
        response_body = json.loads(response_body)
        outputs = response_body.get("outputs")
        if outputs:
            bedrock_attrs["response.choices.finish_reason"] = outputs[0]["stop_reason"]
            bedrock_attrs["output_message_list"] = [
                {"role": "assistant", "content": result["text"]} for result in outputs
            ]
    return bedrock_attrs


def extract_bedrock_titan_text_model_streaming_response(response_body, bedrock_attrs):
    if response_body:
        if "outputText" in response_body:
            bedrock_attrs["output_message_list"] = messages = bedrock_attrs.get("output_message_list", [])
            messages.append({"role": "assistant", "content": response_body["outputText"]})

        bedrock_attrs["response.choices.finish_reason"] = response_body.get("completionReason", None)

    return bedrock_attrs


def extract_bedrock_mistral_text_model_streaming_response(response_body, bedrock_attrs):
    if response_body:
        outputs = response_body.get("outputs")
        if outputs:
            bedrock_attrs["output_message_list"] = bedrock_attrs.get(
                "output_message_list", [{"role": "assistant", "content": ""}]
            )
            bedrock_attrs["output_message_list"][0]["content"] += outputs[0].get("text", "")
            bedrock_attrs["response.choices.finish_reason"] = outputs[0].get("stop_reason", None)
    return bedrock_attrs


def extract_bedrock_titan_embedding_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)

    bedrock_attrs["input"] = request_body.get("inputText")

    return bedrock_attrs


def extract_bedrock_cohere_embedding_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)

    bedrock_attrs["input"] = request_body.get("texts")

    return bedrock_attrs


def extract_bedrock_ai21_j2_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt")}]

    bedrock_attrs["request.max_tokens"] = request_body.get("maxTokens")
    bedrock_attrs["request.temperature"] = request_body.get("temperature")
    bedrock_attrs["input_message_list"] = input_message_list

    return bedrock_attrs


def extract_bedrock_ai21_j2_model_response(response_body, bedrock_attrs):
    if response_body:
        response_body = json.loads(response_body)
        output_message_list = [
            {"role": "assistant", "content": result["data"]["text"]} for result in response_body.get("completions", [])
        ]

        bedrock_attrs["response.choices.finish_reason"] = response_body["completions"][0]["finishReason"]["reason"]
        bedrock_attrs["output_message_list"] = output_message_list
        bedrock_attrs["response_id"] = str(response_body.get("id"))

    return bedrock_attrs


def extract_bedrock_claude_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)

    if "messages" in request_body:
        input_message_list = [
            {"role": message.get("role", "user"), "content": message.get("content")}
            for message in request_body.get("messages")
        ]
    else:
        input_message_list = [{"role": "user", "content": request_body.get("prompt")}]
    bedrock_attrs["request.max_tokens"] = request_body.get("max_tokens_to_sample")
    bedrock_attrs["request.temperature"] = request_body.get("temperature")
    bedrock_attrs["input_message_list"] = input_message_list

    return bedrock_attrs


def extract_bedrock_claude_model_response(response_body, bedrock_attrs):
    if response_body:
        response_body = json.loads(response_body)
        role = response_body.get("role", "assistant")
        content = response_body.get("content") or response_body.get("completion")
        output_message_list = [{"role": role, "content": content}]
        bedrock_attrs["response.choices.finish_reason"] = response_body.get("stop_reason")
        bedrock_attrs["output_message_list"] = output_message_list

    return bedrock_attrs


def extract_bedrock_claude_model_streaming_response(response_body, bedrock_attrs):
    if response_body:
        content = response_body.get("completion", "") or (response_body.get("delta") or {}).get("text", "")
        if "output_message_list" not in bedrock_attrs:
            bedrock_attrs["output_message_list"] = [{"role": "assistant", "content": ""}]
        bedrock_attrs["output_message_list"][0]["content"] += content
        bedrock_attrs["response.choices.finish_reason"] = response_body.get("stop_reason")
    return bedrock_attrs


def extract_bedrock_llama_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt")}]

    bedrock_attrs["request.max_tokens"] = request_body.get("max_gen_len")
    bedrock_attrs["request.temperature"] = request_body.get("temperature")
    bedrock_attrs["input_message_list"] = input_message_list

    return bedrock_attrs


def extract_bedrock_llama_model_response(response_body, bedrock_attrs):
    if response_body:
        response_body = json.loads(response_body)

        output_message_list = [{"role": "assistant", "content": response_body.get("generation")}]
        bedrock_attrs["response.choices.finish_reason"] = response_body.get("stop_reason")
        bedrock_attrs["output_message_list"] = output_message_list

    return bedrock_attrs


def extract_bedrock_llama_model_streaming_response(response_body, bedrock_attrs):
    if response_body:
        content = response_body.get("generation")
        if "output_message_list" not in bedrock_attrs:
            bedrock_attrs["output_message_list"] = [{"role": "assistant", "content": ""}]
        bedrock_attrs["output_message_list"][0]["content"] += content
        bedrock_attrs["response.choices.finish_reason"] = response_body.get("stop_reason")
    return bedrock_attrs


def extract_bedrock_cohere_model_request(request_body, bedrock_attrs):
    request_body = json.loads(request_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt")}]

    bedrock_attrs["request.max_tokens"] = request_body.get("max_tokens")
    bedrock_attrs["request.temperature"] = request_body.get("temperature")
    bedrock_attrs["input_message_list"] = input_message_list

    return bedrock_attrs


def extract_bedrock_cohere_model_response(response_body, bedrock_attrs):
    if response_body:
        response_body = json.loads(response_body)

        output_message_list = [
            {"role": "assistant", "content": result["text"]} for result in response_body.get("generations", [])
        ]

        bedrock_attrs["response.choices.finish_reason"] = response_body["generations"][0]["finish_reason"]
        bedrock_attrs["output_message_list"] = output_message_list
        bedrock_attrs["response_id"] = str(response_body.get("id"))

    return bedrock_attrs


def extract_bedrock_cohere_model_streaming_response(response_body, bedrock_attrs):
    if response_body:
        bedrock_attrs["output_message_list"] = messages = bedrock_attrs.get("output_message_list", [])
        messages.extend(
            [{"role": "assistant", "content": result["text"]} for result in response_body.get("generations", [])]
        )

        bedrock_attrs["response.choices.finish_reason"] = response_body["generations"][0]["finish_reason"]
        bedrock_attrs["response_id"] = str(response_body.get("id"))

    return bedrock_attrs


NULL_EXTRACTOR = lambda *args: {}  # Empty extractor that returns nothing
MODEL_EXTRACTORS = [  # Order is important here, avoiding dictionaries
    (
        "amazon.titan-embed",
        extract_bedrock_titan_embedding_model_request,
        NULL_EXTRACTOR,
        NULL_EXTRACTOR,
    ),
    (
        "cohere.embed",
        extract_bedrock_cohere_embedding_model_request,
        NULL_EXTRACTOR,
        NULL_EXTRACTOR,
    ),
    (
        "amazon.titan",
        extract_bedrock_titan_text_model_request,
        extract_bedrock_titan_text_model_response,
        extract_bedrock_titan_text_model_streaming_response,
    ),
    ("ai21.j2", extract_bedrock_ai21_j2_model_request, extract_bedrock_ai21_j2_model_response, NULL_EXTRACTOR),
    (
        "cohere",
        extract_bedrock_cohere_model_request,
        extract_bedrock_cohere_model_response,
        extract_bedrock_cohere_model_streaming_response,
    ),
    (
        "anthropic.claude",
        extract_bedrock_claude_model_request,
        extract_bedrock_claude_model_response,
        extract_bedrock_claude_model_streaming_response,
    ),
    (
        "meta.llama",
        extract_bedrock_llama_model_request,
        extract_bedrock_llama_model_response,
        extract_bedrock_llama_model_streaming_response,
    ),
    (
        "mistral",
        extract_bedrock_mistral_text_model_request,
        extract_bedrock_mistral_text_model_response,
        extract_bedrock_mistral_text_model_streaming_response,
    ),
]


def wrap_bedrock_runtime_invoke_model(response_streaming=False):
    @function_wrapper
    def _wrap_bedrock_runtime_invoke_model(wrapped, instance, args, kwargs):
        # Wrapped function only takes keyword arguments, no need for binding
        transaction = current_transaction()

        if not transaction:
            return wrapped(*args, **kwargs)

        settings = transaction.settings if transaction.settings is not None else global_settings()
        if not settings.ai_monitoring.enabled:
            return wrapped(*args, **kwargs)

        transaction.add_ml_model_info("Bedrock", BOTOCORE_VERSION)
        transaction._add_agent_attribute("llm", True)

        # Read and replace request file stream bodies
        request_body = kwargs["body"]
        if hasattr(request_body, "read"):
            request_body = request_body.read()
            kwargs["body"] = request_body

        # Determine model to be used with extractor
        model = kwargs.get("modelId")
        if not model:
            return wrapped(*args, **kwargs)

        is_embedding = "embed" in model

        # Determine extractor by model type
        for extractor_name, request_extractor, response_extractor, stream_extractor in MODEL_EXTRACTORS:
            if model.startswith(extractor_name):
                break
        else:
            # Model was not found in extractor list
            global UNSUPPORTED_MODEL_WARNING_SENT
            if not UNSUPPORTED_MODEL_WARNING_SENT:
                # Only send warning once to avoid spam
                _logger.warning(
                    "Unsupported Amazon Bedrock model in use (%s). Upgrade to a newer version of the agent, and contact New Relic support if the issue persists.",
                    model,
                )
                UNSUPPORTED_MODEL_WARNING_SENT = True

            request_extractor = response_extractor = stream_extractor = NULL_EXTRACTOR

        function_name = wrapped.__name__
        operation = "embedding" if is_embedding else "completion"

        # Function trace may not be exited in this function in the case of streaming, so start manually
        ft = FunctionTrace(name=function_name, group="Llm/%s/Bedrock" % (operation))
        ft.__enter__()

        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id")
        trace_id = available_metadata.get("trace.id")

        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            try:
                bedrock_attrs = {
                    "model": model,
                    "span_id": span_id,
                    "trace_id": trace_id,
                }
                try:
                    request_extractor(request_body, bedrock_attrs)
                except json.decoder.JSONDecodeError:
                    pass
                except Exception:
                    _logger.warning(REQUEST_EXTACTOR_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

                error_attributes = bedrock_error_attributes(exc, bedrock_attrs)
                notice_error_attributes = {
                    "http.statusCode": error_attributes.get("http.statusCode"),
                    "error.message": error_attributes.get("error.message"),
                    "error.code": error_attributes.get("error.code"),
                }

                if is_embedding:
                    notice_error_attributes.update({"embedding_id": str(uuid.uuid4())})
                else:
                    notice_error_attributes.update({"completion_id": str(uuid.uuid4())})

                ft.notice_error(
                    attributes=notice_error_attributes,
                )

                ft.__exit__(*sys.exc_info())
                error_attributes["duration"] = ft.duration * 1000

                if operation == "embedding":
                    handle_embedding_event(transaction, error_attributes)
                else:
                    handle_chat_completion_event(transaction, error_attributes)
            except Exception:
                _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

            raise

        if not response or response_streaming and not settings.ai_monitoring.streaming.enabled:
            ft.__exit__(None, None, None)
            return response

        if response_streaming and operation == "embedding":
            # This combination is not supported at time of writing, but may become
            # a supported feature in the future. Instrumentation will need to be written
            # if this becomes available.
            _logger.warning(EMBEDDING_STREAMING_UNSUPPORTED_LOG_MESSAGE)
            ft.__exit__(None, None, None)
            return response

        response_headers = response.get("ResponseMetadata", {}).get("HTTPHeaders") or {}
        bedrock_attrs = {
            "request_id": response_headers.get("x-amzn-requestid"),
            "model": model,
            "span_id": span_id,
            "trace_id": trace_id,
        }

        try:
            request_extractor(request_body, bedrock_attrs)
        except json.decoder.JSONDecodeError:
            pass
        except Exception:
            _logger.warning(REQUEST_EXTACTOR_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

        try:
            if response_streaming:
                # Wrap EventStream object here to intercept __iter__ method instead of instrumenting class.
                # This class is used in numerous other services in botocore, and would cause conflicts.
                response["body"] = body = EventStreamWrapper(response["body"])
                body._nr_ft = ft
                body._nr_bedrock_attrs = bedrock_attrs
                body._nr_model_extractor = stream_extractor
                return response

            # Read and replace response streaming bodies
            response_body = response["body"].read()
            ft.__exit__(None, None, None)
            bedrock_attrs["duration"] = ft.duration * 1000
            response["body"] = StreamingBody(BytesIO(response_body), len(response_body))

            # Run response extractor for non-streaming responses
            try:
                response_extractor(response_body, bedrock_attrs)
            except Exception:
                _logger.warning(RESPONSE_EXTRACTOR_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

            if operation == "embedding":
                handle_embedding_event(transaction, bedrock_attrs)
            else:
                handle_chat_completion_event(transaction, bedrock_attrs)

        except Exception:
            _logger.warning(RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

        return response

    return _wrap_bedrock_runtime_invoke_model


class EventStreamWrapper(ObjectProxy):
    def __iter__(self):
        g = GeneratorProxy(self.__wrapped__.__iter__())
        g._nr_ft = getattr(self, "_nr_ft", None)
        g._nr_bedrock_attrs = getattr(self, "_nr_bedrock_attrs", {})
        g._nr_model_extractor = getattr(self, "_nr_model_extractor", NULL_EXTRACTOR)
        return g


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
            record_stream_chunk(self, return_val, transaction)
        except StopIteration:
            record_events_on_stop_iteration(self, transaction)
            raise
        except Exception as exc:
            record_error(self, transaction, exc)
            raise
        return return_val

    def close(self):
        return super(GeneratorProxy, self).close()


def record_stream_chunk(self, return_val, transaction):
    if return_val:
        try:
            chunk = json.loads(return_val["chunk"]["bytes"].decode("utf-8"))
            self._nr_model_extractor(chunk, self._nr_bedrock_attrs)
            # In Langchain, the bedrock iterator exits early if type is "content_block_stop".
            # So we need to call the record events here since stop iteration will not be raised.
            _type = chunk.get("type")
            if _type == "content_block_stop":
                record_events_on_stop_iteration(self, transaction)
        except Exception:
            _logger.warning(RESPONSE_EXTRACTOR_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))


def record_events_on_stop_iteration(self, transaction):
    if hasattr(self, "_nr_ft"):
        bedrock_attrs = getattr(self, "_nr_bedrock_attrs", {})
        self._nr_ft.__exit__(None, None, None)

        # If there are no bedrock attrs exit early as there's no data to record.
        if not bedrock_attrs:
            return

        try:
            bedrock_attrs["duration"] = self._nr_ft.duration * 1000
            handle_chat_completion_event(transaction, bedrock_attrs)
        except Exception:
            _logger.warning(RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

        # Clear cached data as this can be very large.
        self._nr_bedrock_attrs.clear()


def record_error(self, transaction, exc):
    if hasattr(self, "_nr_ft"):
        try:
            ft = self._nr_ft
            error_attributes = getattr(self, "_nr_bedrock_attrs", {})

            # If there are no bedrock attrs exit early as there's no data to record.
            if not error_attributes:
                return

            error_attributes = bedrock_error_attributes(exc, error_attributes)
            notice_error_attributes = {
                "http.statusCode": error_attributes.get("http.statusCode"),
                "error.message": error_attributes.get("error.message"),
                "error.code": error_attributes.get("error.code"),
            }
            notice_error_attributes.update({"completion_id": str(uuid.uuid4())})

            ft.notice_error(
                attributes=notice_error_attributes,
            )

            ft.__exit__(*sys.exc_info())
            error_attributes["duration"] = ft.duration * 1000

            handle_chat_completion_event(transaction, error_attributes)

            # Clear cached data as this can be very large.
            error_attributes.clear()
        except Exception:
            _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))


def handle_embedding_event(transaction, bedrock_attrs):
    embedding_id = str(uuid.uuid4())

    settings = transaction.settings if transaction.settings is not None else global_settings()

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    span_id = bedrock_attrs.get("span_id", None)
    trace_id = bedrock_attrs.get("trace_id", None)
    request_id = bedrock_attrs.get("request_id", None)
    model = bedrock_attrs.get("model", None)
    input = bedrock_attrs.get("input")

    embedding_dict = {
        "vendor": "bedrock",
        "ingest_source": "Python",
        "id": embedding_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "token_count": (
            settings.ai_monitoring.llm_token_count_callback(model, input)
            if settings.ai_monitoring.llm_token_count_callback
            else None
        ),
        "request_id": request_id,
        "duration": bedrock_attrs.get("duration", None),
        "request.model": model,
        "response.model": model,
        "error": bedrock_attrs.get("error", None),
    }
    embedding_dict.update(llm_metadata_dict)

    if settings.ai_monitoring.record_content.enabled:
        embedding_dict["input"] = input

    embedding_dict = {k: v for k, v in embedding_dict.items() if v is not None}
    transaction.record_custom_event("LlmEmbedding", embedding_dict)


def handle_chat_completion_event(transaction, bedrock_attrs):
    chat_completion_id = str(uuid.uuid4())

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    span_id = bedrock_attrs.get("span_id", None)
    trace_id = bedrock_attrs.get("trace_id", None)
    request_id = bedrock_attrs.get("request_id", None)
    response_id = bedrock_attrs.get("response_id", None)
    model = bedrock_attrs.get("model", None)

    settings = transaction.settings if transaction.settings is not None else global_settings()

    input_message_list = bedrock_attrs.get("input_message_list", [])
    output_message_list = bedrock_attrs.get("output_message_list", [])
    number_of_messages = (
        len(input_message_list) + len(output_message_list)
    ) or None  # If 0, attribute will be set to None and removed

    chat_completion_summary_dict = {
        "vendor": "bedrock",
        "ingest_source": "Python",
        "id": chat_completion_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "request_id": request_id,
        "response_id": response_id,
        "duration": bedrock_attrs.get("duration", None),
        "request.max_tokens": bedrock_attrs.get("request.max_tokens", None),
        "request.temperature": bedrock_attrs.get("request.temperature", None),
        "request.model": model,
        "response.model": model,  # Duplicate data required by the UI
        "response.number_of_messages": number_of_messages,
        "response.choices.finish_reason": bedrock_attrs.get("response.choices.finish_reason", None),
        "error": bedrock_attrs.get("error", None),
    }
    chat_completion_summary_dict.update(llm_metadata_dict)
    chat_completion_summary_dict = {k: v for k, v in chat_completion_summary_dict.items() if v is not None}

    transaction.record_custom_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    create_chat_completion_message_event(
        transaction=transaction,
        input_message_list=input_message_list,
        output_message_list=output_message_list,
        chat_completion_id=chat_completion_id,
        span_id=span_id,
        trace_id=trace_id,
        request_model=model,
        request_id=request_id,
        llm_metadata_dict=llm_metadata_dict,
        response_id=response_id,
    )


CUSTOM_TRACE_POINTS = {
    ("sns", "publish"): message_trace("SNS", "Produce", "Topic", extract(("TopicArn", "TargetArn"), "PhoneNumber")),
    ("dynamodb", "put_item"): datastore_trace("DynamoDB", extract("TableName"), "put_item"),
    ("dynamodb", "get_item"): datastore_trace("DynamoDB", extract("TableName"), "get_item"),
    ("dynamodb", "update_item"): datastore_trace("DynamoDB", extract("TableName"), "update_item"),
    ("dynamodb", "delete_item"): datastore_trace("DynamoDB", extract("TableName"), "delete_item"),
    ("dynamodb", "create_table"): datastore_trace("DynamoDB", extract("TableName"), "create_table"),
    ("dynamodb", "delete_table"): datastore_trace("DynamoDB", extract("TableName"), "delete_table"),
    ("dynamodb", "query"): datastore_trace("DynamoDB", extract("TableName"), "query"),
    ("dynamodb", "scan"): datastore_trace("DynamoDB", extract("TableName"), "scan"),
    ("sqs", "send_message"): message_trace(
        "SQS", "Produce", "Queue", extract_sqs, extract_agent_attrs=extract_agent_attrs
    ),
    ("sqs", "send_message_batch"): message_trace(
        "SQS", "Produce", "Queue", extract_sqs, extract_agent_attrs=extract_agent_attrs
    ),
    ("sqs", "receive_message"): message_trace(
        "SQS", "Consume", "Queue", extract_sqs, extract_agent_attrs=extract_agent_attrs
    ),
    ("bedrock-runtime", "invoke_model"): wrap_bedrock_runtime_invoke_model(response_streaming=False),
    ("bedrock-runtime", "invoke_model_with_response_stream"): wrap_bedrock_runtime_invoke_model(
        response_streaming=True
    ),
}


def bind__create_api_method(py_operation_name, operation_name, service_model, *args, **kwargs):
    return (py_operation_name, service_model)


def _nr_clientcreator__create_api_method_(wrapped, instance, args, kwargs):
    (py_operation_name, service_model) = bind__create_api_method(*args, **kwargs)

    service_name = service_model.service_name.lower()
    tracer = CUSTOM_TRACE_POINTS.get((service_name, py_operation_name))

    wrapped = wrapped(*args, **kwargs)

    if not tracer:
        return wrapped

    return tracer(wrapped)


def _nr_clientcreator__create_methods(wrapped, instance, args, kwargs):
    class_attributes = wrapped(*args, **kwargs)
    class_attributes["_nr_wrapped"] = True
    return class_attributes


def _bind_make_request_params(operation_model, request_dict, *args, **kwargs):
    return operation_model, request_dict


def _nr_endpoint_make_request_(wrapped, instance, args, kwargs):
    operation_model, request_dict = _bind_make_request_params(*args, **kwargs)
    url = request_dict.get("url")
    method = request_dict.get("method")

    with ExternalTrace(library="botocore", url=url, method=method, source=wrapped) as trace:
        try:
            trace._add_agent_attribute("aws.operation", operation_model.name)
        except:
            pass

        result = wrapped(*args, **kwargs)
        try:
            request_id = result[1]["ResponseMetadata"]["RequestId"]
            trace._add_agent_attribute("aws.requestId", request_id)
        except:
            pass
        return result


def instrument_botocore_endpoint(module):
    wrap_function_wrapper(module, "Endpoint.make_request", _nr_endpoint_make_request_)


def instrument_botocore_client(module):
    wrap_function_wrapper(module, "ClientCreator._create_api_method", _nr_clientcreator__create_api_method_)
    wrap_function_wrapper(module, "ClientCreator._create_methods", _nr_clientcreator__create_methods)
