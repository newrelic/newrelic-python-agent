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

import asyncio

import aiohttp
import pytest
from testing_support.fixtures import cat_enabled, validate_transaction_metrics
from yarl import URL

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace

version_info = tuple(int(_) for _ in aiohttp.__version__.split(".")[:2])


async def fetch(method, url):
    async with aiohttp.ClientSession() as session:
        _method = getattr(session, method)
        async with _method(url) as response:
            response.raise_for_status()
            return await response.text()


@background_task(name="fetch_multiple")
async def fetch_multiple(method, url):
    coros = [fetch(method, url) for _ in range(2)]
    return await asyncio.gather(*coros, return_exceptions=True)


if version_info < (2, 0):
    _expected_error_class = aiohttp.errors.HttpProcessingError
else:
    _expected_error_class = aiohttp.client_exceptions.ClientResponseError


def task(loop, method, exc_expected, url):
    text_list = loop.run_until_complete(fetch_multiple(method, url))
    if exc_expected:
        assert isinstance(text_list[0], _expected_error_class), text_list[0].__class__
        assert isinstance(text_list[1], _expected_error_class), text_list[1].__class__
    else:
        assert text_list[0] == text_list[1], text_list


test_matrix = (
    ("get", False),
    ("post", True),
    ("options", True),
    ("head", True),
    ("put", True),
    ("patch", True),
    ("delete", True),
)


@cat_enabled
@pytest.mark.parametrize("method,exc_expected", test_matrix)
def test_client_async_await(event_loop, local_server_info, method, exc_expected):
    @validate_transaction_metrics(
        "fetch_multiple",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
    )
    def task_test():
        task(event_loop, method, exc_expected, local_server_info.url)

    task_test()


@cat_enabled
def test_client_yarl_async_await(event_loop, local_server_info):
    method = "get"

    @validate_transaction_metrics(
        "fetch_multiple",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
    )
    def task_test():
        task(event_loop, method, False, URL(local_server_info.url))

    task_test()


@pytest.mark.parametrize("method,exc_expected", test_matrix)
@cat_enabled
def test_client_no_txn_async_await(event_loop, local_server_info, method, exc_expected):
    def task_test():
        task(event_loop, method, exc_expected, local_server_info.url)

    task_test()


@pytest.mark.parametrize("method,exc_expected", test_matrix)
def test_client_throw_async_await(event_loop, local_server_info, method, exc_expected):
    class ThrowerException(ValueError):
        pass

    @background_task(name="test_client_throw_async_await")
    async def self_driving_thrower():
        async with aiohttp.ClientSession() as session:
            coro = session._request(method.upper(), local_server_info.url)

            # activate the coroutine
            coro.send(None)

            # inject error
            coro.throw(ThrowerException())

    @validate_transaction_metrics(
        "test_client_throw_async_await",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + method.upper(), 1),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + method.upper(), 1),
        ],
    )
    def task_test():
        with pytest.raises(ThrowerException):
            event_loop.run_until_complete(self_driving_thrower())

    task_test()


@pytest.mark.parametrize("method,exc_expected", test_matrix)
def test_client_close_async_await(event_loop, local_server_info, method, exc_expected):
    @background_task(name="test_client_close_async_await")
    async def self_driving_closer():
        async with aiohttp.ClientSession() as session:
            coro = session._request(method.upper(), local_server_info.url)

            # activate the coroutine
            coro.send(None)

            # force close
            coro.close()

    @validate_transaction_metrics(
        "test_client_close_async_await",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + method.upper(), 1),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + method.upper(), 1),
        ],
    )
    def task_test():
        event_loop.run_until_complete(self_driving_closer())

    task_test()


@pytest.mark.parametrize("method,exc_expected", test_matrix)
@cat_enabled
def test_await_request_async_await(event_loop, local_server_info, method, exc_expected):
    async def request_with_await():
        async with aiohttp.ClientSession() as session:
            coro = session._request(method.upper(), local_server_info.url)

            # force await
            result = await coro
            result.raise_for_status()
            return await result.text()

    @validate_transaction_metrics(
        "test_await_request_async_await",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
    )
    @background_task(name="test_await_request_async_await")
    def task_test():
        coros = [request_with_await() for _ in range(2)]
        future = asyncio.gather(*coros, return_exceptions=True)
        text_list = event_loop.run_until_complete(future)
        if exc_expected:
            assert isinstance(text_list[0], _expected_error_class), text_list[0].__class__
            assert isinstance(text_list[1], _expected_error_class), text_list[1].__class__
        else:
            assert text_list[0] == text_list[1], text_list

    task_test()


test_ws_matrix = (
    # the 127.0.0.1 server does not accept websocket requests, hence an
    # exception is expected but a metric will still be created
    ("ws_connect", True),
)


@pytest.mark.parametrize("method,exc_expected", test_ws_matrix)
def test_ws_connect_async_await(event_loop, local_server_info, method, exc_expected):
    @validate_transaction_metrics(
        "fetch_multiple",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + "GET", 2),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + "GET", 2),
        ],
    )
    def task_test():
        task(event_loop, method, exc_expected, local_server_info.url)

    task_test()


@pytest.mark.parametrize("method,exc_expected", test_matrix)
@cat_enabled
def test_create_task_async_await(event_loop, local_server_info, method, exc_expected):

    # `loop.create_task` returns a Task object which uses the coroutine's
    # `send` method, not `__next__`

    async def fetch_task(loop):
        async with aiohttp.ClientSession() as session:
            coro = getattr(session, method)
            resp = await loop.create_task(coro(local_server_info.url))
            resp.raise_for_status()
            return await resp.text()

    @background_task(name="test_create_task_async_await")
    async def fetch_multiple(loop):
        coros = [fetch_task(loop) for _ in range(2)]
        return await asyncio.gather(*coros, return_exceptions=True)

    @validate_transaction_metrics(
        "test_create_task_async_await",
        background_task=True,
        scoped_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
        rollup_metrics=[
            (local_server_info.base_metric + method.upper(), 2),
        ],
    )
    def task_test():
        result = event_loop.run_until_complete(fetch_multiple(event_loop))
        if exc_expected:
            assert isinstance(result[0], _expected_error_class), result[0].__class__
            assert isinstance(result[1], _expected_error_class), result[1].__class__
        else:
            assert result[0] == result[1]

    task_test()


@pytest.mark.parametrize("method,exc_expected", test_matrix)
@cat_enabled
def test_terminal_parent_async_await(event_loop, local_server_info, method, exc_expected):
    """
    This test injects a terminal node into a simple background task workflow.
    It was added to validate a bug where our coro.send() wrapper would fail
    when transaction's current node was terminal.
    """

    def task_test():
        @function_trace(terminal=True)
        def execute_task():
            task(event_loop, method, exc_expected, local_server_info.url)

        execute_task()

    task_test()
