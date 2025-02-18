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
import traceback
import sys
from aiobotocore.response import StreamingBody
from io import BytesIO

from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.hooks.external_botocore import (
    handle_bedrock_exception,
    run_bedrock_response_extractor,
    run_bedrock_request_extractor,
    RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE,
)

_logger = logging.getLogger(__name__)


# Class from https://github.com/aio-libs/aiobotocore/blob/master/tests/test_response.py
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
    # This instrumentation only applies to bedrock runtimes so exit if this method was hit through a different path
    if not hasattr(instance, "_is_bedrock"):
        return await wrapped(*args, **kwargs)

    transaction = instance._nr_txn
    if not transaction:
        return await wrapped(*args, **kwargs)

    # Grab all context data from botocore invoke_model instrumentation off the shared instance
    trace_id = instance._nr_trace_id if hasattr(instance, "_nr_trace_id") else ""
    span_id = instance._nr_span_id if hasattr(instance, "_nr_span_id") else ""
    if hasattr(instance, "_nr_request_extractor"):
        request_extractor = instance._nr_request_extractor
    if hasattr(instance, "_nr_response_extractor"):
        response_extractor = instance._nr_response_extractor
    if hasattr(instance, "_nr_ft"):
        ft = instance._nr_ft

    model = args[1].get("modelId")
    is_embedding = "embed" in model
    request_body = args[1].get("body")

    try:
        response = await wrapped(*args, **kwargs)
    except Exception as exc:
        handle_bedrock_exception(
            exc, is_embedding, model, span_id, trace_id, request_extractor, request_body, ft, transaction
        )

    if not response:
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
        # Read and replace response streaming bodies
        response_body = await response["body"].read()
        if ft:
            ft.__exit__(None, None, None)
            bedrock_attrs["duration"] = ft.duration * 1000
        response["body"] = StreamingBody(AsyncBytesIO(response_body), len(response_body))

        run_bedrock_response_extractor(response_extractor, response_body, bedrock_attrs, is_embedding, transaction)

    except Exception:
        _logger.warning(RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE % traceback.format_exception(*sys.exc_info()))

    return response


def instrument_aiobotocore_endpoint(module):
    wrap_function_wrapper(module, "AioEndpoint.make_request", wrap_endpoint_make_request)


def instrument_aiobotocore_client(module):
    if hasattr(module, "AioBaseClient"):
        wrap_function_wrapper(module, "AioBaseClient._make_api_call", wrap_client__make_api_call)
