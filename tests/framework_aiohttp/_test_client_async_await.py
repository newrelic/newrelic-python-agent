import asyncio
import aiohttp
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from testing_support.fixtures import validate_transaction_metrics

URLS = ['http://example.com', 'http://example.org']


async def fetch(method, url):
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        _method = getattr(session, method)
        async with _method(url) as response:
            return await response.text()


async def fetch_multiple(method):
    coros = [fetch(method, url) for url in URLS]
    return await asyncio.gather(*coros, return_exceptions=True)


def task(loop, method, exc_expected):
    text_list = loop.run_until_complete(fetch_multiple(method))
    if exc_expected:
        assert isinstance(text_list[0],
                aiohttp.client_exceptions.ClientResponseError)
        assert isinstance(text_list[1],
                aiohttp.client_exceptions.ClientResponseError)
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


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client(method, exc_expected):

    @validate_transaction_metrics(
        '_test_client_async_await:test_client.<locals>.task_test',
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
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_no_txn(method, exc_expected):

    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_throw(method, exc_expected):

    class ThrowerException(ValueError):
        pass

    async def self_driving_thrower():
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = session._request(method.upper(), URLS[0])

            # activate the coroutine
            next(coro)

            # inject error
            coro.throw(ThrowerException())

    @validate_transaction_metrics(
        '_test_client_async_await:test_client_throw.<locals>.task_test',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
    )
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()

        with pytest.raises(ThrowerException):
            loop.run_until_complete(self_driving_thrower())

    task_test()


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_close(method, exc_expected):

    async def self_driving_closer():
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = session._request(method.upper(), URLS[0])

            # activate the coroutine
            next(coro)

            # force close
            coro.close()

    @validate_transaction_metrics(
        '_test_client_async_await:test_client_close.<locals>.task_test',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp/%s' % method.upper(), 1),
        ],
    )
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self_driving_closer())

    task_test()


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_await_request(method, exc_expected):

    async def request_with_await(url):
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = session._request(method.upper(), url)

            # force await
            result = await coro
            return await result.text()

    @validate_transaction_metrics(
        '_test_client_async_await:test_await_request.<locals>.task_test',
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
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        coros = [request_with_await(u) for u in URLS]
        future = asyncio.gather(*coros, return_exceptions=True)
        text_list = loop.run_until_complete(future)
        if exc_expected:
            assert isinstance(text_list[0],
                    aiohttp.client_exceptions.ClientResponseError)
            assert isinstance(text_list[1],
                    aiohttp.client_exceptions.ClientResponseError)
        else:
            assert text_list[0] == text_list[1]

    task_test()


test_ws_matrix = (
    # example.com and example.org do not accept websocket requests, hence an
    # exception is expected but a metric will still be created
    ('ws_connect', True),
)


@pytest.mark.parametrize('method,exc_expected', test_ws_matrix)
def test_ws_connect(method, exc_expected):

    @validate_transaction_metrics(
        '_test_client_async_await:test_ws_connect.<locals>.task_test',
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
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_create_task(method, exc_expected):

    # `loop.create_task` returns a Task object which uses the coroutine's
    # `send` method, not `__next__`

    async def fetch_task(url, loop):
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = getattr(session, method)
            resp = await loop.create_task(coro(url))
            return await resp.text()

    async def fetch_multiple(loop):
        coros = [fetch_task(url, loop) for url in URLS]
        return await asyncio.gather(*coros, return_exceptions=True)

    @validate_transaction_metrics(
        '_test_client_async_await:test_create_task.<locals>.task_test',
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
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(fetch_multiple(loop))
        if exc_expected:
            assert isinstance(result[0],
                    aiohttp.client_exceptions.ClientResponseError)
            assert isinstance(result[1],
                    aiohttp.client_exceptions.ClientResponseError)
        else:
            assert result[0] == result[1]

    task_test()


@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_terminal_parent(method, exc_expected):
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
