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

from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper


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
            # Because AIOBotocore's proxy functionality uses aiohttp
            # and urllib3 under the hood, New Relic has portions that
            # are classified as Web Transactions.  This means that
            # browser monitoring will now be true.  However, this will
            # inject unwanted JS Agent Header Fragments into SQS responses.
            trace.settings.browser_monitoring.enabled = False
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


def instrument_aiobotocore_endpoint(module):
    wrap_function_wrapper(module, "AioEndpoint.make_request", wrap_endpoint_make_request)
