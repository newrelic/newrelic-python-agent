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

from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import message_trace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.core.attribute import MAX_LOG_MESSAGE_LENGTH
from newrelic.core.config import global_settings

from botocore.response import StreamingBody


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


def check_rate_limit_header(response_headers, header_name, is_int):
    if not response_headers:
        return ""

    if header_name in response_headers:
        header_value = response_headers.get(header_name)
        if is_int:
            header_value = int(header_value)
        return header_value
    else:
        return ""


def create_chat_completion_message_event(transaction, app_name, message_list, chat_completion_id, span_id, trace_id, request_model, response_id, request_id):
    if not transaction:
        return

    for index, message in enumerate(message_list):
        chat_completion_message_dict = {
            "id": "%s-%s" % (response_id, index),
            "appName": app_name,
            "request_id": request_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction._transaction_id,
            "content": message.get("content", "")[:MAX_LOG_MESSAGE_LENGTH],
            "role": message.get("role"),
            "completion_id": chat_completion_id,
            "sequence": index,
            "request.model": request_model,
            "vendor": "bedrock",
            "ingest_source": "Python",
        }
        transaction.record_ml_event("LlmChatCompletionMessage", chat_completion_message_dict)


def extract_bedrock_titan_model(request_body, response_body):
    response_body = json.loads(response_body)
    request_body = json.loads(request_body)

    input_tokens = response_body["inputTextTokenCount"]
    completion_tokens = sum(result["tokenCount"] for result in response_body["results"])
    total_tokens = input_tokens + completion_tokens

    request_config = request_body.get("textGenerationConfig", {})
    message_list = [{"role": "user", "content": request_body.get("inputText", "")}]
    message_list.extend({"role": "assistant", "content": result["outputText"]} for result in response_body.get("results", []))

    chat_completion_summary_dict = {
        "request.max_tokens": request_config.get("maxTokenCount", ""),
        "request.temperature": request_config.get("temperature", ""),
        "response.choices.finish_reason": response_body["results"][0]["completionReason"],
        "response.usage.completion_tokens": completion_tokens,
        "response.usage.prompt_tokens": input_tokens,
        "response.usage.total_tokens": total_tokens,
        "number_of_messages": len(response_body.get("results", [])) + 1,
    }
    return message_list, chat_completion_summary_dict


MODEL_EXTRACTORS = {
    "amazon.titan": extract_bedrock_titan_model,
}


@function_wrapper
def wrap_bedrock_runtime_invoke_model(wrapped, instance, args, kwargs):
    # Wrapped function only takes keyword arguments, no need for binding
    
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    # Read and replace request file stream bodies
    request_body = kwargs["body"]
    if hasattr(request_body, "read"):
        request_body = request_body.read()
        kwargs["body"] = request_body

    ft_name = callable_name(wrapped)
    with FunctionTrace(ft_name) as ft:
        response = wrapped(*args, **kwargs)

    if not response:
        return response

    # Determine model to be used with extractor
    model = kwargs.get("modelId")
    if not model:
        return response
    
    # Determine extractor by model type
    for extractor_name, extractor in MODEL_EXTRACTORS.items():
        if model.startswith(extractor_name):
            break
    else:
        # Model was not found in extractor list
        global UNSUPPORTED_MODEL_WARNING_SENT
        if not UNSUPPORTED_MODEL_WARNING_SENT:
            # Only send warning once to avoid spam
            _logger.warning("Unsupported Amazon Bedrock model in use (%s). Upgrade to a newer version of the agent, and contact New Relic support if the issue persists.", model)
            UNSUPPORTED_MODEL_WARNING_SENT = True
        
        return response

    # Read and replace response streaming bodies
    response_body = response["body"].read()
    response["body"] = StreamingBody(BytesIO(response_body), len(response_body))

    custom_attrs_dict = transaction._custom_params
    conversation_id = custom_attrs_dict.get("conversation_id", "")

    chat_completion_id = str(uuid.uuid4())
    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")

    response_headers = response["ResponseMetadata"]["HTTPHeaders"]
    request_id = response_headers.get("x-amzn-requestid", "")
    settings = transaction.settings if transaction.settings is not None else global_settings()

    message_list, chat_completion_summary_dict = extractor(request_body, response_body)
    chat_completion_summary_dict.update({
        "vendor": "bedrock",
        "ingest_source": "Python",
        "api_key_last_four_digits": instance._request_signer._credentials.access_key[-4:],
        "id": chat_completion_id,
        "appName": settings.app_name,
        "conversation_id": conversation_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction._transaction_id,
        "request_id": request_id,
        "duration": ft.duration,
        "request.model": model,
    })

    transaction.record_ml_event("LlmChatCompletionSummary", chat_completion_summary_dict)

    create_chat_completion_message_event(
        transaction,
        settings.app_name,
        message_list,
        chat_completion_id,
        span_id,
        trace_id,
        model,
        None,  # TODO: Response ID? Make it a random UUID4
        request_id,
    )

    return response


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
