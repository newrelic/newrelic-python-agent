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
import uuid
from io import BytesIO

from botocore.response import StreamingBody
from botocore.eventstream import EventStream

from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import message_trace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.config import global_settings

BOTOCORE_VERSION = get_package_version("botocore")


_logger = logging.getLogger(__name__)
UNSUPPORTED_MODEL_WARNING_SENT = False


def extract_sqs(*args, **kwargs):
    queue_value = kwargs.get("QueueUrl", "Unknown")
    return queue_value.rsplit("/", 1)[-1]


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


def bedrock_error_attributes(exception, request_args, client, extractor):
    response = getattr(exception, "response", None)
    if not response:
        return {}

    request_body = request_args.get("body", "")
    error_attributes = extractor(request_body)[2]

    error_attributes.update(
        {
            "request_id": response.get("ResponseMetadata", {}).get("RequestId", ""),
            "api_key_last_four_digits": client._request_signer._credentials.access_key[-4:],
            "request.model": request_args.get("modelId", ""),
            "vendor": "bedrock",
            "ingest_source": "Python",
            "http.statusCode": response.get("ResponseMetadata", "").get("HTTPStatusCode", ""),
            "error.message": response.get("Error", "").get("Message", ""),
            "error.code": response.get("Error", "").get("Code", ""),
        }
    )
    return error_attributes


def create_chat_completion_message_event(
    transaction,
    app_name,
    input_message_list,
    output_message_list,
    chat_completion_id,
    span_id,
    trace_id,
    request_model,
    request_id,
    conversation_id,
    response_id="",
):
    if not transaction:
        return

    message_ids = []
    for index, message in enumerate(input_message_list):
        if response_id:
            id_ = "%s-%d" % (response_id, index)  # Response ID was set, append message index to it.
        else:
            id_ = str(uuid.uuid4())  # No response IDs, use random UUID

        chat_completion_message_dict = {
            "id": id_,
            "appName": app_name,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction.guid,
            "content": message.get("content", ""),
            "role": message.get("role"),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": request_model,
            "vendor": "bedrock",
            "ingest_source": "Python",
        }
        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_message_dict)

    for index, message in enumerate(output_message_list):
        index += len(input_message_list)

        if response_id:
            id_ = "%s-%d" % (response_id, index)  # Response ID was set, append message index to it.
        else:
            id_ = str(uuid.uuid4())  # No response IDs, use random UUID
        message_ids.append(id_)

        chat_completion_message_dict = {
            "id": id_,
            "appName": app_name,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction.guid,
            "content": message.get("content", ""),
            "role": message.get("role"),
            "completion_id": chat_completion_id,
            "sequence": index,
            "response.model": request_model,
            "vendor": "bedrock",
            "ingest_source": "Python",
            "is_response": True,
        }
        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_message_dict)
    return (conversation_id, request_id, message_ids)


def extract_bedrock_titan_text_model(request_body, response_body=None):
    request_body = json.loads(request_body)
    if response_body:
        response_body = json.loads(response_body)

    request_config = request_body.get("textGenerationConfig", {})

    input_message_list = [{"role": "user", "content": request_body.get("inputText", "")}]

    chat_completion_summary_dict = {
        "request.max_tokens": request_config.get("maxTokenCount", ""),
        "request.temperature": request_config.get("temperature", ""),
        "response.number_of_messages": len(input_message_list),
    }

    if response_body:
        input_tokens = response_body["inputTextTokenCount"]
        completion_tokens = sum(result["tokenCount"] for result in response_body.get("results", []))
        total_tokens = input_tokens + completion_tokens

        output_message_list = [
            {"role": "assistant", "content": result["outputText"]} for result in response_body.get("results", [])
        ]

        chat_completion_summary_dict.update(
            {
                "response.choices.finish_reason": response_body["results"][0]["completionReason"],
                "response.usage.completion_tokens": completion_tokens,
                "response.usage.prompt_tokens": input_tokens,
                "response.usage.total_tokens": total_tokens,
                "response.number_of_messages": len(input_message_list) + len(output_message_list),
            }
        )
    else:
        output_message_list = []

    return input_message_list, output_message_list, chat_completion_summary_dict


def extract_bedrock_titan_embedding_model(request_body, response_body=None):
    if not response_body:
        return [], [], {}  # No extracted information necessary for embedding

    request_body = json.loads(request_body)
    response_body = json.loads(response_body)

    input_tokens = response_body.get("inputTextTokenCount", None)

    embedding_dict = {
        "input": request_body.get("inputText", ""),
        "response.usage.prompt_tokens": input_tokens,
        "response.usage.total_tokens": input_tokens,
    }
    return [], [], embedding_dict


def extract_bedrock_ai21_j2_model(request_body, response_body=None):
    request_body = json.loads(request_body)
    if response_body:
        response_body = json.loads(response_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt", "")}]

    chat_completion_summary_dict = {
        "request.max_tokens": request_body.get("maxTokens", ""),
        "request.temperature": request_body.get("temperature", ""),
        "response.number_of_messages": len(input_message_list),
    }

    if response_body:
        output_message_list = [
            {"role": "assistant", "content": result["data"]["text"]} for result in response_body.get("completions", [])
        ]

        chat_completion_summary_dict.update(
            {
                "response.choices.finish_reason": response_body["completions"][0]["finishReason"]["reason"],
                "response.number_of_messages": len(input_message_list) + len(output_message_list),
                "response_id": str(response_body.get("id", "")),
            }
        )
    else:
        output_message_list = []

    return input_message_list, output_message_list, chat_completion_summary_dict


def extract_bedrock_claude_model(request_body, response_body=None):
    request_body = json.loads(request_body)
    if response_body:
        response_body = json.loads(response_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt", "")}]

    chat_completion_summary_dict = {
        "request.max_tokens": request_body.get("max_tokens_to_sample", ""),
        "request.temperature": request_body.get("temperature", ""),
        "response.number_of_messages": len(input_message_list),
    }

    if response_body:
        output_message_list = [{"role": "assistant", "content": response_body.get("completion", "")}]

        chat_completion_summary_dict.update(
            {
                "response.choices.finish_reason": response_body.get("stop_reason", ""),
                "response.number_of_messages": len(input_message_list) + len(output_message_list),
            }
        )
    else:
        output_message_list = []

    return input_message_list, output_message_list, chat_completion_summary_dict


def extract_bedrock_llama_model(request_body, response_body=None):
    request_body = json.loads(request_body)
    if response_body:
        response_body = json.loads(response_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt", "")}]

    chat_completion_summary_dict = {
        "request.max_tokens": request_body.get("max_gen_len", ""),
        "request.temperature": request_body.get("temperature", ""),
        "response.number_of_messages": len(input_message_list),
    }

    if response_body:
        output_message_list = [{"role": "assistant", "content": response_body.get("generation", "")}]
        prompt_tokens = response_body.get("prompt_token_count", None)
        completion_tokens = response_body.get("generation_token_count", None)
        total_tokens = prompt_tokens + completion_tokens if prompt_tokens and completion_tokens else None

        chat_completion_summary_dict.update(
            {
                "response.usage.completion_tokens": completion_tokens,
                "response.usage.prompt_tokens": prompt_tokens,
                "response.usage.total_tokens": total_tokens,
                "response.choices.finish_reason": response_body.get("stop_reason", ""),
                "response.number_of_messages": len(input_message_list) + len(output_message_list),
            }
        )
    else:
        output_message_list = []

    return input_message_list, output_message_list, chat_completion_summary_dict


def extract_bedrock_cohere_model(request_body, response_body=None):
    request_body = json.loads(request_body)
    if response_body:
        response_body = json.loads(response_body)

    input_message_list = [{"role": "user", "content": request_body.get("prompt", "")}]

    chat_completion_summary_dict = {
        "request.max_tokens": request_body.get("max_tokens", ""),
        "request.temperature": request_body.get("temperature", ""),
        "response.number_of_messages": len(input_message_list),
    }

    if response_body:
        output_message_list = [
            {"role": "assistant", "content": result["text"]} for result in response_body.get("generations", [])
        ]
        chat_completion_summary_dict.update(
            {
                "response.choices.finish_reason": response_body["generations"][0]["finish_reason"],
                "response.number_of_messages": len(input_message_list) + len(output_message_list),
                "response_id": str(response_body.get("id", "")),
            }
        )
    else:
        output_message_list = []

    return input_message_list, output_message_list, chat_completion_summary_dict


MODEL_EXTRACTORS = [  # Order is important here, avoiding dictionaries
    ("amazon.titan-embed", extract_bedrock_titan_embedding_model),
    ("amazon.titan", extract_bedrock_titan_text_model),
    ("ai21.j2", extract_bedrock_ai21_j2_model),
    ("cohere", extract_bedrock_cohere_model),
    ("anthropic.claude", extract_bedrock_claude_model),
    ("meta.llama2", extract_bedrock_llama_model),
]


@function_wrapper
def wrap_bedrock_runtime_invoke_model(wrapped, instance, args, kwargs):
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

    is_embedding = model.startswith("amazon.titan-embed")

    # Determine extractor by model type
    for extractor_name, extractor in MODEL_EXTRACTORS:
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

        extractor = lambda *args: ([], [], {})  # Empty extractor that returns nothing

    span_id = None
    trace_id = None

    span_id = None
    trace_id = None

    function_name = wrapped.__name__
    operation = "embedding" if model.startswith("amazon.titan-embed") else "completion"

    with FunctionTrace(name=function_name, group="Llm/%s/Bedrock" % (operation)) as ft:
        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id", "")
        trace_id = available_metadata.get("trace.id", "")

        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            try:
                error_attributes = extractor(request_body)
                error_attributes = bedrock_error_attributes(exc, kwargs, instance, extractor)
                notice_error_attributes = {
                    "http.statusCode": error_attributes["http.statusCode"],
                    "error.message": error_attributes["error.message"],
                    "error.code": error_attributes["error.code"],
                }

                if is_embedding:
                    notice_error_attributes.update({"embedding_id": str(uuid.uuid4())})
                else:
                    notice_error_attributes.update({"completion_id": str(uuid.uuid4())})

                ft.notice_error(
                    attributes=notice_error_attributes,
                )

                if operation == "embedding":  # Only available embedding models
                    handle_embedding_event(
                        instance,
                        transaction,
                        extractor,
                        model,
                        None,
                        None,
                        request_body,
                        ft.duration,
                        True,
                        trace_id,
                        span_id,
                    )
                else:
                    handle_chat_completion_event(
                        instance,
                        transaction,
                        extractor,
                        model,
                        None,
                        None,
                        request_body,
                        ft.duration,
                        True,
                        trace_id,
                        span_id,
                    )

            finally:
                raise

    if not response:
        return response

    # Read and replace response streaming bodies
    response_body = response["body"].read()
    response["body"] = StreamingBody(BytesIO(response_body), len(response_body))
    response_headers = response["ResponseMetadata"]["HTTPHeaders"]

    if operation == "embedding":  # Only available embedding models
        handle_embedding_event(
            instance,
            transaction,
            extractor,
            model,
            response_body,
            response_headers,
            request_body,
            ft.duration,
            False,
            trace_id,
            span_id,
        )
    else:
        handle_chat_completion_event(
            instance,
            transaction,
            extractor,
            model,
            response_body,
            response_headers,
            request_body,
            ft.duration,
            False,
            trace_id,
            span_id,
        )

    return response

@function_wrapper
def wrap_bedrock_runtime_invoke_model_with_response_stream(wrapped, instance, args, kwargs):
    # Wrapped function only takes keyword arguments, no need for binding

    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    # Read and replace request file stream bodies
    request_body = kwargs["body"]
    if hasattr(request_body, "read"):
        request_body = request_body.read()
        kwargs["body"] = request_body

    # Determine model to be used with extractor
    model = kwargs.get("modelId")
    if not model:
        return wrapped(*args, **kwargs)

    # Determine extractor by model type
    for extractor_name, extractor in MODEL_EXTRACTORS:
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
        
        extractor = lambda *args: ([], {})  # Empty extractor that returns nothing

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            try:
                error_attributes = extractor(request_body)
                error_attributes = bedrock_error_attributes(exc, kwargs, instance, extractor)
                ft.notice_error(
                    attributes=error_attributes,
                )
            finally:
                raise

    if not response:
        return response

    # Read and replace response streaming bodies
    # breakpoint()
    # response_body = list(response["body"])
    # response["body"] = EventStream(response_body)
    response_headers = response["ResponseMetadata"]["HTTPHeaders"]

    if model.startswith("amazon.titan-embed"):  # Only available embedding models
        handle_embedding_event(
            instance, transaction, extractor, model, None, response_headers, request_body, ft.duration
        )
    else:
        handle_chat_completion_event(
            instance, transaction, extractor, model, None, response_headers, request_body, ft.duration
        )

    return response


def handle_embedding_event(
    client,
    transaction,
    extractor,
    model,
    response_body,
    response_headers,
    request_body,
    duration,
    is_error,
    trace_id,
    span_id,
):
    embedding_id = str(uuid.uuid4())

    request_id = response_headers.get("x-amzn-requestid", "") if response_headers else ""

    settings = transaction.settings if transaction.settings is not None else global_settings()

    _, _, embedding_dict = extractor(request_body, response_body)

    request_body = json.loads(request_body)

    embedding_dict.update(
        {
            "vendor": "bedrock",
            "ingest_source": "Python",
            "id": embedding_id,
            "appName": settings.app_name,
            "span_id": span_id,
            "trace_id": trace_id,
            "request_id": request_id,
            "input": request_body.get("inputText", ""),
            "transaction_id": transaction.guid,
            "api_key_last_four_digits": client._request_signer._credentials.access_key[-4:],
            "duration": duration,
            "request.model": model,
            "response.model": model,
        }
    )
    if is_error:
        embedding_dict.update({"error": True})

    transaction.record_custom_event("LlmEmbedding", embedding_dict)


def handle_chat_completion_event(
    client,
    transaction,
    extractor,
    model,
    response_body,
    response_headers,
    request_body,
    duration,
    is_error,
    trace_id,
    span_id,
):
    custom_attrs_dict = transaction._custom_params
    conversation_id = custom_attrs_dict.get("llm.conversation_id", "")

    chat_completion_id = str(uuid.uuid4())

    request_id = response_headers.get("x-amzn-requestid", "") if response_headers else ""

    settings = transaction.settings if transaction.settings is not None else global_settings()

    input_message_list, output_message_list, chat_completion_summary_dict = extractor(request_body, response_body)
    response_id = chat_completion_summary_dict.get("response_id", "")
    chat_completion_summary_dict.update(
        {
            "vendor": "bedrock",
            "ingest_source": "Python",
            "api_key_last_four_digits": client._request_signer._credentials.access_key[-4:],
            "id": chat_completion_id,
            "appName": settings.app_name,
            "conversation_id": conversation_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction.guid,
            "request_id": request_id,
            "duration": duration,
            "request.model": model,
            "response.model": model,  # Duplicate data required by the UI
        }
    )
    if is_error:
        chat_completion_summary_dict.update({"error": True})

    transaction.record_custom_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    message_ids = create_chat_completion_message_event(
        transaction=transaction,
        app_name=settings.app_name,
        input_message_list=input_message_list,
        output_message_list=output_message_list,
        chat_completion_id=chat_completion_id,
        span_id=span_id,
        trace_id=trace_id,
        request_model=model,
        request_id=request_id,
        conversation_id=conversation_id,
        response_id=response_id,
    )

    if not hasattr(transaction, "_nr_message_ids"):
        transaction._nr_message_ids = {}
    transaction._nr_message_ids["bedrock_key"] = message_ids


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
    ("sqs", "send_message"): message_trace("SQS", "Produce", "Queue", extract_sqs),
    ("sqs", "send_message_batch"): message_trace("SQS", "Produce", "Queue", extract_sqs),
    ("sqs", "receive_message"): message_trace("SQS", "Consume", "Queue", extract_sqs),
    ("bedrock-runtime", "invoke_model"): wrap_bedrock_runtime_invoke_model,
    ("bedrock-runtime", "invoke_model_with_response_stream"): wrap_bedrock_runtime_invoke_model_with_response_stream,
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
    url = request_dict.get("url", "")
    method = request_dict.get("method", None)

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
