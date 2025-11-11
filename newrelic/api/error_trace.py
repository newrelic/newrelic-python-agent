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

from newrelic.api.time_trace import current_trace, notice_error
from newrelic.common.async_wrapper import async_wrapper as get_async_wrapper
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object


class ErrorTrace:
    def __init__(self, ignore=None, expected=None, status_code=None, parent=None):
        if parent is None:
            parent = current_trace()

        self._transaction = parent and parent.transaction
        self._ignore = ignore
        self._expected = expected
        self._status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        if exc is None or value is None or tb is None:
            return

        if self._transaction is None:
            return

        notice_error(
            error=(exc, value, tb), ignore=self._ignore, expected=self._expected, status_code=self._status_code
        )


def ErrorTraceWrapper(wrapped, ignore=None, expected=None, status_code=None, async_wrapper=None):
    def literal_wrapper(wrapped, instance, args, kwargs):
        # Determine if the wrapped function is async or sync
        wrapper = async_wrapper if async_wrapper is not None else get_async_wrapper(wrapped)
        # Sync function path
        if not wrapper:
            parent = current_trace()
            if not parent:
                # No active tracing context so just call the wrapped function directly
                return wrapped(*args, **kwargs)
        # Async function path
        else:
            # For async functions, the async wrapper will handle trace context propagation
            parent = None

        trace = ErrorTrace(ignore, expected, status_code, parent=parent)

        if wrapper:
            # The async wrapper handles the context management for us
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    return FunctionWrapper(wrapped, literal_wrapper)


def error_trace(ignore=None, expected=None, status_code=None):
    return functools.partial(ErrorTraceWrapper, ignore=ignore, expected=expected, status_code=status_code)


def wrap_error_trace(module, object_path, ignore=None, expected=None, status_code=None):
    wrap_object(module, object_path, ErrorTraceWrapper, (ignore, expected, status_code))
