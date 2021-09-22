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

from newrelic.common.object_wrapper import function_wrapper
from newrelic.core.trace_cache import trace_cache

class ContextOf(object):
    def __init__(self, trace_cache_id):
        self.trace_cache = trace_cache()
        self.trace = self.trace_cache._cache.get(trace_cache_id)
        self.thread_id = None
        self.restore = None

    def __enter__(self):
        if self.trace:
            self.thread_id = self.trace_cache.current_thread_id()
            self.restore = self.trace_cache._cache.get(self.thread_id)
            self.trace_cache._cache[self.thread_id] = self.trace
        return self

    def __exit__(self, exc, value, tb):
        if self.restore:
            self.trace_cache._cache[self.thread_id] = self.restore


async def context_wrapper_async(awaitable, trace_cache_id):
    with ContextOf(trace_cache_id):
        return await awaitable


def context_wrapper(func, trace_cache_id):
    @function_wrapper
    def _context_wrapper(wrapped, instance, args, kwargs):
        with ContextOf(trace_cache_id):
            return wrapped(*args, **kwargs)

    return _context_wrapper(func)


def current_thread_id():
    return trace_cache().current_thread_id()
