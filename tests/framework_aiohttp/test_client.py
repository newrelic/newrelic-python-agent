import aiohttp
import asyncio
import pytest
import sys

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from testing_support.fixtures import validate_transaction_metrics

URLS = ['http://example.com', 'http://example.org']

version_info = tuple(int(_) for _ in aiohttp.__version__.split('.'))
skipif_aiohttp3 = pytest.mark.skipif(version_info >= (3, 0),
        reason='This version of aiohttp does not support yield from syntax')


@asyncio.coroutine
def fetch(method, url):
    with aiohttp.ClientSession() as session:
        _method = getattr(session, method)
        response = yield from asyncio.wait_for(_method(url), timeout=None)
        response.raise_for_status()
        yield from response.text()


@asyncio.coroutine
def fetch_multiple(method):
    coros = [fetch(method, url) for url in URLS]
    return asyncio.gather(*coros, return_exceptions=True)


if version_info < (2, 0):
    _expected_error_class = aiohttp.errors.HttpProcessingError
else:
    _expected_error_class = aiohttp.client_exceptions.ClientResponseError


def task(loop, method, exc_expected):
    future = asyncio.ensure_future(fetch_multiple(method))
    text_list = loop.run_until_complete(future)
    if exc_expected:
        assert isinstance(text_list[0], _expected_error_class)
        assert isinstance(text_list[1], _expected_error_class)
    else:
        assert text_list[0] == text_list[1]


test_matrix = (
    ('get', False),
    ('post', False),
    ('options', False),
    ('head', False),
    ('put', True),
    ('patch', True),
    ('delete', True),
)


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_yield_from(method, exc_expected):

    @validate_transaction_metrics(
        'test_client_yield_from',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
            ('External/example.org/aiohttp/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
            ('External/example.org/aiohttp/%s' % method.upper(), 1),
        ],
    )
    @background_task(name='test_client_yield_from')
    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_no_txn_yield_from(method, exc_expected):

    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_throw_yield_from(method, exc_expected):

    class ThrowerException(ValueError):
        pass

    @asyncio.coroutine
    def self_driving_thrower():
        with aiohttp.ClientSession() as session:
            coro = session._request(method.upper(), URLS[0])

            # activate the coroutine
            next(coro)

            # inject error
            coro.throw(ThrowerException())

    @validate_transaction_metrics(
        'test_client_throw_yield_from',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
    )
    @background_task(name='test_client_throw_yield_from')
    def task_test():
        loop = asyncio.get_event_loop()

        with pytest.raises(ThrowerException):
            loop.run_until_complete(self_driving_thrower())

    task_test()


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_close_yield_from(method, exc_expected):

    @asyncio.coroutine
    def self_driving_closer():
        with aiohttp.ClientSession() as session:
            coro = session._request(method.upper(), URLS[0])

            # activate the coroutine
            next(coro)

            # force close
            coro.close()

    @validate_transaction_metrics(
        'test_client_close_yield_from',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
    )
    @background_task(name='test_client_close_yield_from')
    def task_test():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self_driving_closer())

    task_test()


test_ws_matrix = (
    # example.com and example.org do not accept websocket requests, hence an
    # exception is expected but a metric will still be created
    ('ws_connect', True),
)


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_ws_matrix)
def test_ws_connect_yield_from(method, exc_expected):

    @validate_transaction_metrics(
        'test_ws_connect_yield_from',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/GET', 1),
            ('External/example.org/aiohttp/GET', 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/GET', 1),
            ('External/example.org/aiohttp/GET', 1),
        ],
    )
    @background_task(name='test_ws_connect_yield_from')
    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_create_task_yield_from(method, exc_expected):

    # `loop.create_task` returns a Task object which uses the coroutine's
    # `send` method, not `__next__`

    @asyncio.coroutine
    def fetch_task(url, loop):
        with aiohttp.ClientSession() as session:
            coro = getattr(session, method)
            resp = yield from loop.create_task(coro(url))
            resp.raise_for_status()
            yield from resp.text()

    @asyncio.coroutine
    def fetch_multiple(loop):
        coros = [fetch_task(url, loop) for url in URLS]
        return asyncio.gather(*coros, return_exceptions=True)

    @validate_transaction_metrics(
        'test_create_task_yield_from',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
            ('External/example.org/aiohttp/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
            ('External/example.org/aiohttp/%s' % method.upper(), 1),
        ],
    )
    @background_task(name='test_create_task_yield_from')
    def task_test():
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(fetch_multiple(loop))
        if exc_expected:
            assert isinstance(result[0], _expected_error_class)
            assert isinstance(result[1], _expected_error_class)
        else:
            assert result[0] == result[1]

    task_test()


@skipif_aiohttp3
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_terminal_node_yield_from(method, exc_expected):
    """
    This test injects a terminal node into a simple background task workflow.
    It was added to validate a bug where our coro.send() wrapper would fail
    when transaction's current node was terminal.
    """

    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()

        @function_trace(terminal=True)
        def execute_task():
            task(loop, method, exc_expected)

        execute_task()

    task_test()


if sys.version_info >= (3, 5):
    from _test_client_async_await import *  # NOQA
