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

import inspect
import json
import logging
import re
import sys
import traceback
import uuid
from io import BytesIO

from botocore.response import StreamingBody

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import MessageTrace, message_trace
from newrelic.api.time_trace import current_trace, get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.async_wrapper import async_wrapper as get_async_wrapper
from newrelic.common.object_wrapper import ObjectProxy, function_wrapper, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
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


def extract_kinesis(*args, **kwargs):
    # The stream name can be passed as the StreamName or as part of the StreamARN, ResourceARN, or ConsumerARN.
    stream_name = kwargs.get("StreamName", None)
    if stream_name is not None:
        return stream_name

    arn = kwargs.get("StreamARN", None) or kwargs.get("ResourceARN", None) or kwargs.get("ConsumerARN", None)
    if arn is not None:
        return arn.split("/")[1]


def extract_firehose(*args, **kwargs):
    return kwargs.get("DeliveryStreamName", None)


def extract_sqs_agent_attrs(instance, *args, **kwargs):
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
    except Exception:
        _logger.debug("Failed to capture AWS SQS info.", exc_info=True)
    return agent_attrs


def extract_kinesis_agent_attrs(instance, *args, **kwargs):
    # Try to capture AWS Kinesis ARN from the StreamARN, ConsumerARN, or ResourceARN parameters, or by generating the
    # ARN from various discoverable info. Log any exception to debug.
    agent_attrs = {}
    try:
        stream_arn = kwargs.get("StreamARN", None)
        if stream_arn is not None:
            agent_attrs["cloud.platform"] = "aws_kinesis_data_streams"
            agent_attrs["cloud.resource_id"] = stream_arn
            return agent_attrs

        stream_name = kwargs.get("StreamName", None)
        if stream_name is not None:
            transaction = current_transaction()
            settings = transaction.settings if transaction.settings else global_settings()
            account_id = settings.cloud.aws.account_id if settings and settings.cloud.aws.account_id else None
            region = None
            if hasattr(instance, "_client_config") and hasattr(instance._client_config, "region_name"):
                region = instance._client_config.region_name
            if stream_name and account_id and region:
                agent_attrs["cloud.platform"] = "aws_kinesis_data_streams"
                agent_attrs["cloud.resource_id"] = f"arn:aws:kinesis:{region}:{account_id}:stream/{stream_name}"

        resource_arn = kwargs.get("ResourceARN", None) or kwargs.get("ConsumerARN", None)
        if resource_arn is not None:
            # Extract just the StreamARN out of ConsumerARNs.
            agent_attrs["cloud.resource_id"] = "/".join(resource_arn.split("/")[0:2])
            agent_attrs["cloud.platform"] = "aws_kinesis_data_streams"
            return agent_attrs

    except Exception:
        _logger.debug("Failed to capture AWS Kinesis info.", exc_info=True)
    return agent_attrs


def extract_firehose_agent_attrs(instance, *args, **kwargs):
    # Try to generate AWS Kinesis Delivery Stream (Firehose) ARN from the DeliveryStreamName parameter and from various
    # discoverable info. Log any exception to debug.
    agent_attrs = {}
    try:
        stream_name = kwargs.get("DeliveryStreamName", None)
        if stream_name:
            transaction = current_transaction()
            settings = transaction.settings if transaction.settings else global_settings()
            account_id = settings.cloud.aws.account_id if settings and settings.cloud.aws.account_id else None
            region = None
            if hasattr(instance, "_client_config") and hasattr(instance._client_config, "region_name"):
                region = instance._client_config.region_name
            if account_id and region:
                agent_attrs["cloud.platform"] = "aws_kinesis_delivery_streams"
                agent_attrs["cloud.resource_id"] = (
                    f"arn:aws:firehose:{region}:{account_id}:deliverystream/{stream_name}"
                )
    except Exception:
        _logger.debug("Failed to capture AWS Kinesis Delivery Stream (Firehose) info.", exc_info=True)
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
            id_ = f"{response_id}-{int(index)}"  # Response ID was set, append message index to it.
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
            id_ = f"{response_id}-{int(index)}"  # Response ID was set, append message index to it.
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


NULL_EXTRACTOR = lambda *args: {}  # noqa: E731  # Empty extractor that returns nothing
MODEL_EXTRACTORS = [  # Order is important here, avoiding dictionaries
    ("amazon.titan-embed", extract_bedrock_titan_embedding_model_request, NULL_EXTRACTOR, NULL_EXTRACTOR),
    ("cohere.embed", extract_bedrock_cohere_embedding_model_request, NULL_EXTRACTOR, NULL_EXTRACTOR),
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


def handle_bedrock_exception(
    exc, is_embedding, model, span_id, trace_id, request_extractor, request_body, ft, transaction
):
    try:
        bedrock_attrs = {"model": model, "span_id": span_id, "trace_id": trace_id}
        try:
            request_extractor(request_body, bedrock_attrs)
        except json.decoder.JSONDecodeError:
            pass
        except Exception:
            _logger.warning(REQUEST_EXTACTOR_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

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

        if ft:
            ft.notice_error(attributes=notice_error_attributes)

            ft.__exit__(*sys.exc_info())
            error_attributes["duration"] = ft.duration * 1000

        if is_embedding:
            handle_embedding_event(transaction, error_attributes)
        else:
            handle_chat_completion_event(transaction, error_attributes)
    except Exception:
        _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


def run_bedrock_response_extractor(response_extractor, response_body, bedrock_attrs, is_embedding, transaction):
    # Run response extractor for non-streaming responses
    try:
        response_extractor(response_body, bedrock_attrs)
    except Exception:
        _logger.warning(RESPONSE_EXTRACTOR_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

    if is_embedding:
        handle_embedding_event(transaction, bedrock_attrs)
    else:
        handle_chat_completion_event(transaction, bedrock_attrs)


def run_bedrock_request_extractor(request_extractor, request_body, bedrock_attrs):
    try:
        request_extractor(request_body, bedrock_attrs)
    except json.decoder.JSONDecodeError:
        pass
    except Exception:
        _logger.warning(REQUEST_EXTACTOR_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


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
        for extractor_name, request_extractor, response_extractor, stream_extractor in MODEL_EXTRACTORS:  # noqa: B007
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
        ft = FunctionTrace(name=function_name, group=f"Llm/{operation}/Bedrock")
        ft.__enter__()

        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id")
        trace_id = available_metadata.get("trace.id")

        # Store data on instance to pass context to async instrumentation
        instance._nr_trace_id = trace_id
        instance._nr_span_id = span_id
        instance._nr_request_extractor = request_extractor
        instance._nr_response_extractor = response_extractor
        instance._nr_stream_extractor = stream_extractor
        instance._nr_txn = transaction
        instance._nr_ft = ft
        instance._nr_response_streaming = response_streaming
        instance._nr_settings = settings

        # Add a bedrock flag to instance so we can determine when make_api_call instrumentation is hit from non-Bedrock paths and bypass it if so
        instance._nr_is_bedrock = True

        try:
            # For aioboto3 clients, this will call make_api_call instrumentation in external_aiobotocore
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            handle_bedrock_exception(
                exc, is_embedding, model, span_id, trace_id, request_extractor, request_body, ft, transaction
            )
            raise

        if not response or response_streaming and not settings.ai_monitoring.streaming.enabled:
            ft.__exit__(None, None, None)
            return response

        # Let the instrumentation of make_api_call in the aioboto3 client handle it if we have an async case
        if inspect.iscoroutine(response):
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

        run_bedrock_request_extractor(request_extractor, request_body, bedrock_attrs)

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

            run_bedrock_response_extractor(response_extractor, response_body, bedrock_attrs, is_embedding, transaction)

        except Exception:
            _logger.warning(RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

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
        super().__init__(wrapped)

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
        return super().close()


class AsyncEventStreamWrapper(ObjectProxy):
    def __aiter__(self):
        g = AsyncGeneratorProxy(self.__wrapped__.__aiter__())
        g._nr_ft = getattr(self, "_nr_ft", None)
        g._nr_bedrock_attrs = getattr(self, "_nr_bedrock_attrs", {})
        g._nr_model_extractor = getattr(self, "_nr_model_extractor", NULL_EXTRACTOR)
        return g


class AsyncGeneratorProxy(ObjectProxy):
    def __init__(self, wrapped):
        super().__init__(wrapped)

    def __aiter__(self):
        return self

    async def __anext__(self):
        transaction = current_transaction()
        if not transaction:
            return await self.__wrapped__.__anext__()
        return_val = None
        try:
            return_val = await self.__wrapped__.__anext__()
            record_stream_chunk(self, return_val, transaction)
        except StopAsyncIteration:
            record_events_on_stop_iteration(self, transaction)
            raise
        except Exception as exc:
            record_error(self, transaction, exc)
            raise
        return return_val

    async def aclose(self):
        return await super().aclose()


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
            _logger.warning(RESPONSE_EXTRACTOR_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


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
            _logger.warning(RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

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

            ft.notice_error(attributes=notice_error_attributes)

            ft.__exit__(*sys.exc_info())
            error_attributes["duration"] = ft.duration * 1000

            handle_chat_completion_event(transaction, error_attributes)

            # Clear cached data as this can be very large.
            error_attributes.clear()
        except Exception:
            _logger.warning(EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))


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
    input_ = bedrock_attrs.get("input")

    embedding_dict = {
        "vendor": "bedrock",
        "ingest_source": "Python",
        "id": embedding_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "token_count": (
            settings.ai_monitoring.llm_token_count_callback(model, input_)
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
        embedding_dict["input"] = input_

    embedding_dict = {k: v for k, v in embedding_dict.items() if v is not None}
    transaction.record_custom_event("LlmEmbedding", embedding_dict)


def handle_chat_completion_event(transaction, bedrock_attrs):
    chat_completion_id = str(uuid.uuid4())

    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}

    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)
    span_id = bedrock_attrs.get("span_id", None)
    trace_id = bedrock_attrs.get("trace_id", None)
    request_id = bedrock_attrs.get("request_id", None)
    response_id = bedrock_attrs.get("response_id", None)
    model = bedrock_attrs.get("model", None)

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


def dynamodb_datastore_trace(
    product, target, operation, host=None, port_path_or_id=None, database_name=None, async_wrapper=None
):
    @function_wrapper
    def _nr_dynamodb_datastore_trace_wrapper_(wrapped, instance, args, kwargs):
        wrapper = async_wrapper if async_wrapper is not None else get_async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        if callable(product):
            if instance is not None:
                _product = product(instance, *args, **kwargs)
            else:
                _product = product(*args, **kwargs)
        else:
            _product = product

        if callable(target):
            if instance is not None:
                _target = target(instance, *args, **kwargs)
            else:
                _target = target(*args, **kwargs)
        else:
            _target = target

        if callable(operation):
            if instance is not None:
                _operation = operation(instance, *args, **kwargs)
            else:
                _operation = operation(*args, **kwargs)
        else:
            _operation = operation

        if callable(host):
            if instance is not None:
                _host = host(instance, *args, **kwargs)
            else:
                _host = host(*args, **kwargs)
        else:
            _host = host

        if callable(port_path_or_id):
            if instance is not None:
                _port_path_or_id = port_path_or_id(instance, *args, **kwargs)
            else:
                _port_path_or_id = port_path_or_id(*args, **kwargs)
        else:
            _port_path_or_id = port_path_or_id

        if callable(database_name):
            if instance is not None:
                _database_name = database_name(instance, *args, **kwargs)
            else:
                _database_name = database_name(*args, **kwargs)
        else:
            _database_name = database_name

        trace = DatastoreTrace(
            _product, _target, _operation, _host, _port_path_or_id, _database_name, parent=parent, source=wrapped
        )

        # Try to capture AWS DynamoDB info as agent attributes. Log any exception to debug.
        agent_attrs = {}
        try:
            region = None
            if hasattr(instance, "_client_config") and hasattr(instance._client_config, "region_name"):
                region = instance._client_config.region_name

            transaction = current_transaction()
            settings = transaction.settings if transaction.settings else global_settings()
            account_id = settings.cloud.aws.account_id if settings and settings.cloud.aws.account_id else None

            # There are 3 different partition options.
            # See  https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html for details.
            partition = None
            if hasattr(instance, "_endpoint") and hasattr(instance._endpoint, "host"):
                _db_host = instance._endpoint.host
                partition = "aws"
                if "amazonaws.cn" in _db_host:
                    partition = "aws-cn"
                elif "amazonaws-us-gov.com" in _db_host:
                    partition = "aws-us-gov"

            if partition and region and account_id and _target:
                agent_attrs["cloud.resource_id"] = (
                    f"arn:{partition}:dynamodb:{region}:{account_id:012d}:table/{_target}"
                )

        except Exception:
            _logger.debug("Failed to capture AWS DynamoDB info.", exc_info=True)
        trace.agent_attributes.update(agent_attrs)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return _nr_dynamodb_datastore_trace_wrapper_


def aws_function_trace(
    operation,
    destination_name=None,
    params=None,
    terminal=False,
    async_wrapper=None,
    extract_agent_attrs=None,
    library=None,
):
    if params is None:
        params = {}

    @function_wrapper
    def _nr_aws_function_trace_wrapper_(wrapped, instance, args, kwargs):
        wrapper = async_wrapper if async_wrapper is not None else get_async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        _destination_name = destination_name(*args, **kwargs) if destination_name is not None else None
        name = f"{operation}/{_destination_name}" if _destination_name else operation

        trace = FunctionTrace(name=name, group=library, params=params, terminal=terminal, parent=parent, source=wrapped)

        # Attach extracted agent attributes.
        _agent_attrs = extract_agent_attrs(instance, *args, **kwargs) if extract_agent_attrs is not None else {}
        trace.agent_attributes.update(_agent_attrs)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return _nr_aws_function_trace_wrapper_


def aws_message_trace(
    operation,
    destination_type,
    destination_name,
    params=None,
    terminal=True,
    async_wrapper=None,
    extract_agent_attrs=None,
    library=None,
):
    if params is None:
        params = {}

    @function_wrapper
    def _nr_aws_message_trace_wrapper_(wrapped, instance, args, kwargs):
        wrapper = async_wrapper if async_wrapper is not None else get_async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        _library = library
        _operation = operation
        _destination_type = destination_type
        _destination_name = destination_name(*args, **kwargs) or "Unknown"

        trace = MessageTrace(
            _library,
            _operation,
            _destination_type,
            _destination_name,
            params=params,
            terminal=terminal,
            parent=parent,
            source=wrapped,
        )

        # Attach extracted agent attributes.
        _agent_attrs = extract_agent_attrs(instance, *args, **kwargs)
        trace.agent_attributes.update(_agent_attrs)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return _nr_aws_message_trace_wrapper_


def wrap_emit_api_params(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)

    api_params = wrapped(*args, **kwargs)

    arn = bound_args.get("api_params").get("FunctionName")
    if arn:
        try:
            if arn.startswith("arn:"):
                api_params["_nr_arn"] = arn
        except Exception:
            pass  # Unable to determine ARN from FunctionName.

    # Wrap instance._serializer.serialize_to_request if not already wrapped.
    if (
        hasattr(instance, "_serializer")
        and hasattr(instance._serializer, "serialize_to_request")
        and not hasattr(instance._serializer, "_nr_wrapped")
    ):

        @function_wrapper
        def wrap_serialize_to_request(wrapped, instance, args, kwargs):
            transaction = current_transaction()
            if not transaction:
                return wrapped(*args, **kwargs)

            bound_args = bind_args(wrapped, args, kwargs)

            arn = bound_args.get("parameters", {}).pop("_nr_arn", None)

            request_dict = wrapped(*args, **kwargs)

            if arn:
                request_dict["_nr_arn"] = arn

            return request_dict

        instance._serializer.serialize_to_request = wrap_serialize_to_request(instance._serializer.serialize_to_request)
        instance._serializer._nr_wrapped = True

    return api_params


CUSTOM_TRACE_POINTS = {
    ("sns", "publish"): message_trace("SNS", "Produce", "Topic", extract(("TopicArn", "TargetArn"), "PhoneNumber")),
    ("dynamodb", "put_item"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "put_item"),
    ("dynamodb", "get_item"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "get_item"),
    ("dynamodb", "update_item"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "update_item"),
    ("dynamodb", "delete_item"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "delete_item"),
    ("dynamodb", "create_table"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "create_table"),
    ("dynamodb", "delete_table"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "delete_table"),
    ("dynamodb", "query"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "query"),
    ("dynamodb", "scan"): dynamodb_datastore_trace("DynamoDB", extract("TableName"), "scan"),
    ("kinesis", "add_tags_to_stream"): aws_function_trace(
        "add_tags_to_stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "create_stream"): aws_function_trace(
        "create_stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "decrease_stream_retention_period"): aws_function_trace(
        "decrease_stream_retention_period",
        extract_kinesis,
        extract_agent_attrs=extract_kinesis_agent_attrs,
        library="Kinesis",
    ),
    ("kinesis", "delete_resource_policy"): aws_function_trace(
        "delete_resource_policy", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "delete_stream"): aws_function_trace(
        "delete_stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "deregister_stream_consumer"): aws_function_trace(
        "deregister_stream_consumer",
        extract_kinesis,
        extract_agent_attrs=extract_kinesis_agent_attrs,
        library="Kinesis",
    ),
    ("kinesis", "describe_limits"): aws_function_trace("describe_limits", library="Kinesis"),
    ("kinesis", "describe_stream"): aws_function_trace(
        "describe_stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "describe_stream_consumer"): aws_function_trace(
        "describe_stream_consumer", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "describe_stream_summary"): aws_function_trace(
        "describe_stream_summary", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "disable_enhanced_monitoring"): aws_function_trace(
        "disable_enhanced_monitoring",
        extract_kinesis,
        extract_agent_attrs=extract_kinesis_agent_attrs,
        library="Kinesis",
    ),
    ("kinesis", "enable_enhanced_monitoring"): aws_function_trace(
        "enable_enhanced_monitoring",
        extract_kinesis,
        extract_agent_attrs=extract_kinesis_agent_attrs,
        library="Kinesis",
    ),
    ("kinesis", "get_resource_policy"): aws_function_trace(
        "get_resource_policy", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "get_shard_iterator"): aws_function_trace(
        "get_shard_iterator", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "increase_stream_retention_period"): aws_function_trace(
        "increase_stream_retention_period",
        extract_kinesis,
        extract_agent_attrs=extract_kinesis_agent_attrs,
        library="Kinesis",
    ),
    ("kinesis", "list_shards"): aws_function_trace(
        "list_shards", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "list_stream_consumers"): aws_function_trace(
        "list_stream_consumers", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "list_streams"): aws_function_trace("list_streams", library="Kinesis"),
    ("kinesis", "list_tags_for_resource"): aws_function_trace(
        "list_tags_for_resource", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "list_tags_for_stream"): aws_function_trace(
        "list_tags_for_stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "merge_shards"): aws_function_trace(
        "merge_shards", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "put_resource_policy"): aws_function_trace(
        "put_resource_policy", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "register_stream_consumer"): aws_function_trace(
        "register_stream_consumer", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "remove_tags_from_stream"): aws_function_trace(
        "remove_tags_from_stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "split_shard"): aws_function_trace(
        "split_shard", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "start_stream_encryption"): aws_function_trace(
        "start_stream_encryption", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "stop_stream_encryption"): aws_function_trace(
        "stop_stream_encryption", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "subscribe_to_shard"): aws_function_trace(
        "subscribe_to_shard", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "tag_resource"): aws_function_trace(
        "tag_resource", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "untag_resource"): aws_function_trace(
        "untag_resource", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "update_shard_count"): aws_function_trace(
        "update_shard_count", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "update_stream_mode"): aws_function_trace(
        "update_stream_mode", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "put_record"): aws_message_trace(
        "Produce", "Stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "put_records"): aws_message_trace(
        "Produce", "Stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("kinesis", "get_records"): aws_message_trace(
        "Consume", "Stream", extract_kinesis, extract_agent_attrs=extract_kinesis_agent_attrs, library="Kinesis"
    ),
    ("firehose", "create_delivery_stream"): aws_function_trace(
        "create_delivery_stream", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("firehose", "delete_delivery_stream"): aws_function_trace(
        "delete_delivery_stream", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("firehose", "describe_delivery_stream"): aws_function_trace(
        "describe_delivery_stream",
        extract_firehose,
        extract_agent_attrs=extract_firehose_agent_attrs,
        library="Firehose",
    ),
    ("firehose", "list_delivery_streams"): aws_function_trace("list_delivery_streams", library="Firehose"),
    ("firehose", "list_tags_for_delivery_stream"): aws_function_trace(
        "list_tags_for_delivery_stream",
        extract_firehose,
        extract_agent_attrs=extract_firehose_agent_attrs,
        library="Firehose",
    ),
    ("firehose", "put_record"): aws_function_trace(
        "put_record", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("firehose", "put_record_batch"): aws_function_trace(
        "put_record_batch", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("firehose", "start_delivery_stream_encryption"): aws_function_trace(
        "start_delivery_stream_encryption",
        extract_firehose,
        extract_agent_attrs=extract_firehose_agent_attrs,
        library="Firehose",
    ),
    ("firehose", "stop_delivery_stream_encryption"): aws_function_trace(
        "stop_delivery_stream_encryption",
        extract_firehose,
        extract_agent_attrs=extract_firehose_agent_attrs,
        library="Firehose",
    ),
    ("firehose", "tag_delivery_stream"): aws_function_trace(
        "tag_delivery_stream", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("firehose", "untag_delivery_stream"): aws_function_trace(
        "untag_delivery_stream", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("firehose", "update_destination"): aws_function_trace(
        "update_destination", extract_firehose, extract_agent_attrs=extract_firehose_agent_attrs, library="Firehose"
    ),
    ("sqs", "send_message"): aws_message_trace(
        "Produce", "Queue", extract_sqs, extract_agent_attrs=extract_sqs_agent_attrs, library="SQS"
    ),
    ("sqs", "send_message_batch"): aws_message_trace(
        "Produce", "Queue", extract_sqs, extract_agent_attrs=extract_sqs_agent_attrs, library="SQS"
    ),
    ("sqs", "receive_message"): aws_message_trace(
        "Consume", "Queue", extract_sqs, extract_agent_attrs=extract_sqs_agent_attrs, library="SQS"
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
            bound_args = bind_args(wrapped, args, kwargs)
            lambda_arn = bound_args.get("request_dict").pop("_nr_arn", None)
            if lambda_arn:
                trace._add_agent_attribute("cloud.platform", "aws_lambda")
                trace._add_agent_attribute("cloud.resource_id", lambda_arn)
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
    if hasattr(module, "ClientCreator"):
        wrap_function_wrapper(module, "ClientCreator._create_api_method", _nr_clientcreator__create_api_method_)
        wrap_function_wrapper(module, "ClientCreator._create_methods", _nr_clientcreator__create_methods)
    if hasattr(module, "BaseClient"):
        wrap_function_wrapper(module, "BaseClient._emit_api_params", wrap_emit_api_params)
