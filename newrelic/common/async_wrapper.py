import textwrap
import functools
from newrelic.common.coroutine import (
    is_coroutine_function,
    is_asyncio_coroutine,
    is_generator_function,
)


def evaluate_wrapper(wrapper_string, wrapped, trace):
    values = {'wrapper': None, 'wrapped': wrapped,
            'trace': trace, 'functools': functools}
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
    import asyncio

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


def async_wrapper(wrapped):
    if is_coroutine_function(wrapped):
        return coroutine_wrapper
    elif is_generator_function(wrapped):
        if is_asyncio_coroutine(wrapped):
            return awaitable_generator_wrapper
        else:
            return generator_wrapper
