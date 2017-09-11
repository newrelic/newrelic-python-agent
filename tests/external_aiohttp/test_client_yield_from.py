import asyncio
import aiohttp
import pytest

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics

URLS = ['http://example.com', 'http://example.org']


@asyncio.coroutine
def fetch(method, url, throw=False):
    with aiohttp.ClientSession(raise_for_status=True) as session:
        _method = getattr(session, method)
        response = yield from asyncio.wait_for(_method(url), timeout=None)
        yield from response.text()


@asyncio.coroutine
def fetch_multiple(method):
    coros = [fetch(method, url) for url in URLS]
    return asyncio.gather(*coros, return_exceptions=True)


def task(loop, method, exc_expected):
    future = asyncio.ensure_future(fetch_multiple(method))
    text_list = loop.run_until_complete(future)
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
        'test_client_yield_from:test_client.<locals>.task_test',
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

    @asyncio.coroutine
    def self_driving_thrower():
        with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = session._request(method.upper(), URLS[0])

            # activate the coroutine
            next(coro)

            # inject error
            coro.throw(ThrowerException())

    @validate_transaction_metrics(
        'test_client_yield_from:test_client_throw.<locals>.task_test',
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

    @asyncio.coroutine
    def self_driving_closer():
        with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = session._request(method.upper(), URLS[0])

            # activate the coroutine
            next(coro)

            # force close
            coro.close()

    @validate_transaction_metrics(
        'test_client_yield_from:test_client_close.<locals>.task_test',
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
