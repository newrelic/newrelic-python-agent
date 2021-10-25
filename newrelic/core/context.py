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

"""
This module implements utilities for context propagation for tracing across threads.
"""

import logging
from newrelic.api.time_trace import current_trace

from newrelic.common.object_wrapper import function_wrapper
from newrelic.core.trace_cache import trace_cache

_logger = logging.getLogger(__name__)


class ContextOf(object):
    def __init__(self, trace=None, request=None):
        self.trace = None
        self.trace_cache = trace_cache()
        self.thread_id = None
        self.restore = False

        # Extract trace if possible, else leave as None for safety
        if trace is None and request is None:
            _logger.error(
                "Runtime instrumentation error. Request context propagation failed. No trace or request provided. Report this issue to New Relic support.\n",
            )
        elif trace is not None:
            self.trace = trace
        elif hasattr(request, "_nr_trace") and request._nr_trace is not None:
                # Unpack traces from objects patched with them
                self.trace = request._nr_trace
        else:
            _logger.error(
                "Runtime instrumentation error. Request context propagation failed. No context attached to request. Report this issue to New Relic support.\n",
            )


    def __enter__(self):
        if self.trace:
            self.thread_id = self.trace_cache.current_thread_id()

            if self.thread_id not in self.trace_cache._cache:
                # No active trace for current thread: continue
                self.restore = True
                self.trace_cache._cache[self.thread_id] = self.trace
            elif self.trace_cache._cache[self.thread_id] is self.trace:
                # Trace already active for this thread: ignore
                pass
            else:
                _logger.error(
                    "Runtime instrumentation error. An active trace already exists in the cache on thread_id %s. Report this issue to New Relic support.\n",
                    current_thread_id,
                )
                return None

        return self

    def __exit__(self, exc, value, tb):
        if self.restore:
            self.trace_cache._cache.pop(self.thread_id)


def context_wrapper(func, trace=None, request=None):
    @function_wrapper
    def _context_wrapper(wrapped, instance, args, kwargs):
        with ContextOf(trace=trace, request=request):
            return wrapped(*args, **kwargs)

    return _context_wrapper(func)


def current_thread_id():
    return trace_cache().current_thread_id()
