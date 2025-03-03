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

from newrelic.api.time_trace import current_trace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.core.context import context_wrapper


def instrument_s3transfer_futures(module):
    if hasattr(module, "BoundedExecutor"):
        wrap_function_wrapper(module, "BoundedExecutor.submit", wrap_BoundedExecutor_submit)


def wrap_BoundedExecutor_submit(wrapped, instance, args, kwargs):
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)
    bound_args["task"] = context_wrapper(bound_args["task"], trace=trace, strict=True)

    return wrapped(**bound_args)
