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

from newrelic.common.coroutine import (
    is_async_generator_function,
    is_asyncio_coroutine,
    is_coroutine_callable,
    is_generator_function,
)


def coroutine_wrapper(wrapped, trace):
    @functools.wraps(wrapped)
    async def wrapper(*args, **kwargs):
        with trace:
            return await wrapped(*args, **kwargs)

    return wrapper


def awaitable_generator_wrapper(wrapped, trace):
    import asyncio

    @functools.wraps(wrapped)
    @asyncio.coroutine
    def wrapper(*args, **kwargs):
        with trace:
            result = yield from wrapped(*args, **kwargs)
            return result

    return wrapper


def generator_wrapper(wrapped, trace):
    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        with trace:
            result = yield from wrapped(*args, **kwargs)
            return result

    return wrapper


def async_generator_wrapper(wrapped, trace):
    @functools.wraps(wrapped)
    async def wrapper(*args, **kwargs):
        g = wrapped(*args, **kwargs)
        with trace:
            try:
                yielded = await g.asend(None)
                while True:
                    try:
                        sent = yield yielded
                    except GeneratorExit:
                        await g.aclose()
                        raise
                    except BaseException as e:
                        yielded = await g.athrow(e)
                    else:
                        yielded = await g.asend(sent)
            except StopAsyncIteration:
                return

    return wrapper


def async_wrapper(wrapped):
    if is_coroutine_callable(wrapped):
        return coroutine_wrapper
    elif is_async_generator_function(wrapped):
        return async_generator_wrapper
    elif is_generator_function(wrapped):
        if is_asyncio_coroutine(wrapped):
            return awaitable_generator_wrapper
        else:
            return generator_wrapper
