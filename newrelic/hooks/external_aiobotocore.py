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
import aiohttp
import aiofiles
import traceback
import sys
from aiobotocore.response import StreamingBody
from io import BytesIO

from newrelic.api.transaction import current_transaction
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.time_trace import current_trace, get_trace_linking_metadata
from newrelic.hooks.external_botocore import (
    bedrock_error_attributes,
    handle_embedding_event,
    EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE,
    RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE,
    handle_chat_completion_event,
    REQUEST_EXTACTOR_FAILURE_LOG_MESSAGE,
    MODEL_EXTRACTORS,
    UNSUPPORTED_MODEL_WARNING_SENT,
)

_logger = logging.getLogger(__name__)


class AsyncBytesIO(BytesIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = self

    async def read(self, amt=-1):
        if amt == -1:  # aiohttp to regular response
            amt = None
        return super().read(amt)


def _bind_make_request_params(operation_model, request_dict, *args, **kwargs):
    return operation_model, request_dict


def bind__send_request(request_dict, operation_model, *args, **kwargs):
    return operation_model, request_dict


async def wrap_endpoint_make_request(wrapped, instance, args, kwargs):
    operation_model, request_dict = _bind_make_request_params(*args, **kwargs)
    url = request_dict.get("url")
    method = request_dict.get("method")

    with ExternalTrace(library="aiobotocore", url=url, method=method, source=wrapped) as trace:
        try:
            trace._add_agent_attribute("aws.operation", operation_model.name)
        except:
            pass

        result = await wrapped(*args, **kwargs)
        try:
            request_id = result[1]["ResponseMetadata"]["RequestId"]
            trace._add_agent_attribute("aws.requestId", request_id)
        except:
            pass
        return result


async def wrap_client__make_api_call(wrapped, instance, args, kwargs):
    trace_id = instance._nr_trace_id
    span_id = instance._nr_span_id
    model = args[1].get("modelId")
    is_embedding = "embed" in model
    request_body = args[1].get("body")

    request_extractor = instance._nr_request_extractor
    response_extractor = instance._nr_response_extractor
    transaction = instance._txn

    operation = "embedding" if is_embedding else "completion"
    function_name = wrapped.__name__

    ft = FunctionTrace(name=function_name, group=f"Llm/{operation}/Bedrock")
    ft.__enter__()

    try:
        response = await wrapped(*args, **kwargs)
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

    if not response:
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
        # Read and replace response streaming bodies
        response_body = await response["body"].read()
        ft.__exit__(None, None, None)
        bedrock_attrs["duration"] = ft.duration * 1000
        response["body"] = StreamingBody(AsyncBytesIO(response_body), len(response_body))
        # response_body = await response["body"].read()

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


def instrument_aiobotocore_endpoint(module):
    wrap_function_wrapper(module, "AioEndpoint.make_request", wrap_endpoint_make_request)


def instrument_aiobotocore_client(module):
    if hasattr(module, "AioBaseClient"):
        wrap_function_wrapper(module, "AioBaseClient._make_api_call", wrap_client__make_api_call)
