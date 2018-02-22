import asyncio
import aiohttp
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from testing_support.fixtures import validate_transaction_metrics

URLS = ['http://example.com', 'http://example.org']

version_info = tuple(int(_) for _ in aiohttp.__version__.split('.'))
xfailif_aiohttp1 = pytest.mark.xfail(version_info < (2, 0), strict=True,
        reason='PYTHON-2678')


@asyncio.coroutine
def fetch(method, url):
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


@xfailif_aiohttp1
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


@xfailif_aiohttp1
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_no_txn_yield_from(method, exc_expected):

    def task_test():
        loop = asyncio.get_event_loop()
        task(loop, method, exc_expected)

    task_test()


@xfailif_aiohttp1
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_throw_yield_from(method, exc_expected):

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


@xfailif_aiohttp1
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_client_close_yield_from(method, exc_expected):

    @asyncio.coroutine
    def self_driving_closer():
        with aiohttp.ClientSession(raise_for_status=True) as session:
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


@xfailif_aiohttp1
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


@xfailif_aiohttp1
@pytest.mark.parametrize('method,exc_expected', test_matrix)
def test_create_task_yield_from(method, exc_expected):

    # `loop.create_task` returns a Task object which uses the coroutine's
    # `send` method, not `__next__`

    @asyncio.coroutine
    def fetch_task(url, loop):
        with aiohttp.ClientSession(raise_for_status=True) as session:
            coro = getattr(session, method)
            resp = yield from loop.create_task(coro(url))
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
            assert isinstance(result[0],
                    aiohttp.client_exceptions.ClientResponseError)
            assert isinstance(result[1],
                    aiohttp.client_exceptions.ClientResponseError)
        else:
            assert result[0] == result[1]

    task_test()


@xfailif_aiohttp1
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
