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
import sys
import traceback
from io import BytesIO

from aiobotocore.response import StreamingBody

from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.hooks.external_botocore import (
    EMBEDDING_STREAMING_UNSUPPORTED_LOG_MESSAGE,
    RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE,
    AsyncEventStreamWrapper,
    handle_bedrock_exception,
    run_bedrock_request_extractor,
    run_bedrock_response_extractor,
)

_logger = logging.getLogger(__name__)


# Class from https://github.com/aio-libs/aiobotocore/blob/master/tests/test_response.py
# aiobotocore Apache 2 license: https://github.com/aio-libs/aiobotocore/blob/master/LICENSE
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
    if not hasattr(instance, "_nr_is_bedrock"):
        return await wrapped(*args, **kwargs)

    transaction = getattr(instance, "_nr_txn", None)
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = getattr(instance, "_nr_settings", None)

    # Early exit if we can't access the shared settings object from invoke_model instrumentation
    # This settings object helps us determine if AIM was enabled as well as streaming
    if not (settings and settings.ai_monitoring.enabled):
        return await wrapped(*args, **kwargs)

    # Grab all context data from botocore invoke_model instrumentation off the shared instance
    trace_id = getattr(instance, "_nr_trace_id", "")
    span_id = getattr(instance, "_nr_span_id", "")

    request_extractor = getattr(instance, "_nr_request_extractor", None)
    response_extractor = getattr(instance, "_nr_response_extractor", None)
    stream_extractor = getattr(instance, "_nr_stream_extractor", None)
    response_streaming = getattr(instance, "_nr_response_streaming", False)

    ft = getattr(instance, "_nr_ft", None)

    if len(args) >= 2:
        model = args[1].get("modelId")
        request_body = args[1].get("body")
        is_embedding = "embed" in model
    else:
        model = ""
        request_body = None
        is_embedding = False

    try:
        response = await wrapped(*args, **kwargs)
    except Exception as exc:
        handle_bedrock_exception(
            exc, is_embedding, model, span_id, trace_id, request_extractor, request_body, ft, transaction
        )
        raise

    if not response or response_streaming and not settings.ai_monitoring.streaming.enabled:
        if ft:
            ft.__exit__(None, None, None)
        return response

    if response_streaming and is_embedding:
        # This combination is not supported at time of writing, but may become
        # a supported feature in the future. Instrumentation will need to be written
        # if this becomes available.
        _logger.warning(EMBEDDING_STREAMING_UNSUPPORTED_LOG_MESSAGE)
        if ft:
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
            response["body"] = body = AsyncEventStreamWrapper(response["body"])
            body._nr_ft = ft or None
            body._nr_bedrock_attrs = bedrock_attrs or {}
            body._nr_model_extractor = stream_extractor or None
            return response

        # Read and replace response streaming bodies
        response_body = await response["body"].read()

        if ft:
            ft.__exit__(None, None, None)
            bedrock_attrs["duration"] = ft.duration * 1000
        response["body"] = StreamingBody(AsyncBytesIO(response_body), len(response_body))
        run_bedrock_response_extractor(response_extractor, response_body, bedrock_attrs, is_embedding, transaction)

    except Exception:
        _logger.warning(RESPONSE_PROCESSING_FAILURE_LOG_MESSAGE, traceback.format_exception(*sys.exc_info()))

    return response


def instrument_aiobotocore_endpoint(module):
    wrap_function_wrapper(module, "AioEndpoint.make_request", wrap_endpoint_make_request)


def instrument_aiobotocore_client(module):
    if hasattr(module, "AioBaseClient"):
        wrap_function_wrapper(module, "AioBaseClient._make_api_call", wrap_client__make_api_call)
