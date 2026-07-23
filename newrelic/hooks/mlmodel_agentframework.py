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

from newrelic.api.time_trace import current_trace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.context import ContextOf

_logger = logging.getLogger(__name__)
AGENT_FRAMEWORK_VERSION = get_package_version("agent-framework")
BEDROCK_CONTEXT_FAILURE_MESSAGE = (
    "Failed to grab existing trace and attach to request object in agent_framework_bedrock."
)


def wrap_BedrockChatClient__invoke_converse(wrapped, instance, args, kwargs):
    bound_args = bind_args(wrapped, args, kwargs)

    # Pop the current trace out of the request object and resume it on this thread
    try:
        request = bound_args["request"]
        trace = request.pop("_nr_trace", None)
    except Exception:
        trace = None

    if trace:
        with ContextOf(trace=trace, strict=False):
            return wrapped(*args, **kwargs)
    else:
        return wrapped(*args, **kwargs)


def wrap_BedrockChatClient__prepare_options(wrapped, instance, args, kwargs):
    request = wrapped(*args, **kwargs)

    trace = current_trace()
    if not trace:
        return request

    # Attach the current trace to the request so we can resume it inside the asyncio.to_thread call
    try:
        request["_nr_trace"] = trace
    except Exception:
        _logger.debug(BEDROCK_CONTEXT_FAILURE_MESSAGE)

    return request


def instrument_agent_framwork_bedrock__chat_client(module):
    if hasattr(module, "BedrockChatClient"):
        if hasattr(module.BedrockChatClient, "_invoke_converse"):
            wrap_function_wrapper(module, "BedrockChatClient._invoke_converse", wrap_BedrockChatClient__invoke_converse)

        if hasattr(module.BedrockChatClient, "_prepare_options"):
            wrap_function_wrapper(module, "BedrockChatClient._prepare_options", wrap_BedrockChatClient__prepare_options)
