import pytest
import tornado.gen
import tornado.web

try:
    import _test_iscoroutine_async_await_fixtures as _test_fixtures
except SyntaxError:
    _test_fixtures = None

try:
    import asyncio
except ImportError:
    asyncio = None

from newrelic.hooks.framework_tornado_r4.routing import (
        _iscoroutinefunction_native, _iscoroutinefunction_tornado)


@pytest.mark.skipif(not _test_fixtures,
        reason='Native coroutines not supported in this Python version.')
def test_native_coroutines():
    method = _test_fixtures.Class1().get
    assert _iscoroutinefunction_native(method)
    assert not _iscoroutinefunction_tornado(method)


@pytest.mark.skipif(not asyncio,
        reason='No asyncio module in this Python version.')
def test_asyncio_coroutine_function():

    class Handler(object):
        @asyncio.coroutine
        def get(self):
            pass

    method = Handler().get
    assert _iscoroutinefunction_native(method)
    assert not _iscoroutinefunction_tornado(method)


@pytest.mark.skipif(not asyncio,
        reason='No asyncio module in this Python version.')
def test_asyncio_coroutine_generator():

    class Handler(object):
        @asyncio.coroutine
        def get(self):
            yield

    method = Handler().get
    assert _iscoroutinefunction_native(method)
    assert not _iscoroutinefunction_tornado(method)


def test_tornado_gen_coroutine_function():

    class Handler(object):
        @tornado.gen.coroutine
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_gen_coroutine_generator():

    class Handler(object):
        @tornado.gen.coroutine
        def get(self):
            yield

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_gen_engine_function():

    class Handler(object):
        @tornado.gen.engine
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_gen_engine_generator():

    class Handler(object):
        @tornado.gen.engine
        def get(self):
            yield

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_async_engine_function():

    class Handler(object):
        @tornado.web.asynchronous
        @tornado.gen.engine
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_async_engine_generator():

    class Handler(object):
        @tornado.web.asynchronous
        @tornado.gen.engine
        def get(self):
            yield

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_web_async():

    class Handler(object):
        @tornado.web.asynchronous
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert not _iscoroutinefunction_tornado(method)


def test_just_plain_method():

    class Handler(object):
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert not _iscoroutinefunction_tornado(method)


# For legacy reasons, tornado allows for both decorators to be used at once.
# From their docs: "It is legal for legacy reasons to use the two decorators
# together provided @asynchronous is first, but @asynchronous will be ignored
# in this case." Since we do not know what they mean by "first", we test both
# orderings.

def test_tornado_async_coro_function():

    class Handler(object):
        @tornado.web.asynchronous
        @tornado.gen.coroutine
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_async_coro_generator():

    class Handler(object):
        @tornado.web.asynchronous
        @tornado.gen.coroutine
        def get(self):
            yield

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_coro_async_function():

    class Handler(object):
        @tornado.web.asynchronous
        @tornado.gen.coroutine
        def get(self):
            pass

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)


def test_tornado_coro_async_generator():

    class Handler(object):
        @tornado.web.asynchronous
        @tornado.gen.coroutine
        def get(self):
            yield

    method = Handler().get
    assert not _iscoroutinefunction_native(method)
    assert _iscoroutinefunction_tornado(method)
