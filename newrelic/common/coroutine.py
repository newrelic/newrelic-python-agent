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

import inspect


def is_coroutine_function(wrapped):
    return inspect.iscoroutinefunction(wrapped)


def is_asyncio_coroutine(wrapped):
    """Return True if func is a decorated coroutine function."""
    return getattr(wrapped, "_is_coroutine", None) is not None


def is_generator_function(wrapped):
    return inspect.isgeneratorfunction(wrapped)


def _iscoroutinefunction_tornado(fn):
    return hasattr(fn, "__tornado_coroutine__")


def is_coroutine_callable(wrapped):
    return is_coroutine_function(wrapped) or is_coroutine_function(getattr(wrapped, "__call__", None))  # noqa: B004


if hasattr(inspect, "isasyncgenfunction"):

    def is_async_generator_function(wrapped):
        return inspect.isasyncgenfunction(wrapped)
else:

    def is_async_generator_function(wrapped):
        return False
