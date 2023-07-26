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

import textwrap
import functools
from newrelic.common.coroutine import (
    is_coroutine_callable,
    is_asyncio_coroutine,
    is_generator_function,
    is_async_generator_function,
)

try:
    import asyncio
except ImportError:
    asyncio = None


def evaluate_wrapper(wrapper_string, wrapped, trace):
    values = {'wrapper': None, 'wrapped': wrapped,
            'trace': trace, 'functools': functools, "asyncio": asyncio}
    exec(wrapper_string, values)
    return values['wrapper']


def coroutine_wrapper(wrapped, trace):
    WRAPPER = textwrap.dedent("""
    @functools.wraps(wrapped)
    async def wrapper(*args, **kwargs):
        with trace:
            return await wrapped(*args, **kwargs)
    """)

    try:
        return evaluate_wrapper(WRAPPER, wrapped, trace)
    except Exception:
        return wrapped


def awaitable_generator_wrapper(wrapped, trace):
    WRAPPER = textwrap.dedent("""
    @functools.wraps(wrapped)
    @asyncio.coroutine
    def wrapper(*args, **kwargs):
        with trace:
            result = yield from wrapped(*args, **kwargs)
            return result
    """)

    try:
        return evaluate_wrapper(WRAPPER, wrapped, trace)
    except:
        return wrapped


def generator_wrapper(wrapped, trace):
    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        g = wrapped(*args, **kwargs)
        value = None
        with trace:
            while True:
                try:
                    yielded = g.send(value)
                except StopIteration:
                    break

                try:
                    value = yield yielded
                except BaseException as e:
                    value = yield g.throw(type(e), e)

    return wrapper


def async_generator_wrapper(wrapped, trace):
    WRAPPER = textwrap.dedent("""
    @functools.wraps(wrapped)
    async def wrapper(*args, **kwargs):
        g = wrapped(*args, **kwargs)
        value = None
        with trace:
            while True:
                try:
                    g.asend(value).send(None)
                except StopAsyncIteration as e:
                    # The underlying async generator has finished, return propagates a new StopAsyncIteration
                    return
                except StopIteration as e:
                    # The call to async_generator_asend.send() should raise a StopIteration containing the yielded value
                    yielded = e.value

                try:
                    value = yield yielded
                except BaseException as e:
                    # An exception was thrown with .athrow(), propagate to the original async generator.
                    # Return value logic must be identical to .asend()
                    try:
                        g.athrow(type(e), e).send(None)
                    except StopAsyncIteration as e:
                        # The underlying async generator has finished, return propagates a new StopAsyncIteration
                        return
                    except StopIteration as e:
                        # The call to async_generator_athrow.send() should raise a StopIteration containing a yielded value
                        value = yield e.value
    """)

    try:
        return evaluate_wrapper(WRAPPER, wrapped, trace)
    except:
        return wrapped


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
