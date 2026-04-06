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

import functools
import logging
import sys
import threading
import warnings

from newrelic.api.application import register_application
from newrelic.api.background_task import BackgroundTaskWrapper
from newrelic.api.error_trace import wrap_error_trace
from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper, wrap_function_trace
from newrelic.api.html_insertion import insert_html_snippet
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.api.transaction_name import wrap_transaction_name
from newrelic.api.wsgi_application import WSGIApplicationWrapper
from newrelic.common.coroutine import is_asyncio_coroutine, is_coroutine_function
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import (
    FunctionWrapper,
    function_wrapper,
    wrap_function_wrapper,
    wrap_in_function,
    wrap_post_function,
)
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)

def _nr_wrapper_convert_exception_to_response_(wrapped, instance, args, kwargs):
    def _bind_params(original_middleware, *args, **kwargs):
        return original_middleware

    original_middleware = _bind_params(*args, **kwargs)
    converted_middleware = wrapped(*args, **kwargs)
    name = callable_name(original_middleware)
    do_not_wrap = is_denied_middleware(name)

    if do_not_wrap:
        return converted_middleware
    else:
        if is_coroutine_function(converted_middleware) or is_asyncio_coroutine(converted_middleware):
            return _nr_wrap_converted_middleware_async_(converted_middleware, name)
        return _nr_wrap_converted_middleware_(converted_middleware, name)


def instrument_django_core_handlers_exception(module):
    if hasattr(module, "convert_exception_to_response"):
        wrap_function_wrapper(module, "convert_exception_to_response", _nr_wrapper_convert_exception_to_response_)

    if hasattr(module, "handle_uncaught_exception"):
        module.handle_uncaught_exception = wrap_handle_uncaught_exception(module.handle_uncaught_exception)
