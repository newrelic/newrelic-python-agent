import asyncio
import aiohttp
import pytest

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics

URLS = ['http://example.com', 'http://example.org']


async def fetch(method, url, throw=False):
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
        'test_client:test_client.<locals>.task_test',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp_client/%s' % method.upper(), 1),
            ('External/example.org/aiohttp_client/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp_client/%s' % method.upper(), 1),
            ('External/example.org/aiohttp_client/%s' % method.upper(), 1),
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
        'test_client:test_client_throw.<locals>.task_test',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp_client/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp_client/%s' % method.upper(), 1),
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
        'test_client:test_client_close.<locals>.task_test',
        background_task=True,
        scoped_metrics=[
            ('External/example.com/aiohttp_client/%s' % method.upper(), 1),
        ],
        rollup_metrics=[
            ('External/example.com/aiohttp_client/%s' % method.upper(), 1),
        ],
    )
    @background_task()
    def task_test():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self_driving_closer())

    task_test()
