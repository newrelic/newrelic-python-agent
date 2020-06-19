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
import functools
import pytest
import time

from newrelic.api.background_task import background_task
from newrelic.api.database_trace import database_trace
from newrelic.api.datastore_trace import datastore_trace
from newrelic.api.function_trace import function_trace
from newrelic.api.external_trace import external_trace
from newrelic.api.memcache_trace import memcache_trace
from newrelic.api.message_trace import message_trace

from testing_support.fixtures import (validate_transaction_metrics,
        capture_transaction_metrics)


@pytest.mark.parametrize('trace,metric', [
    (functools.partial(function_trace, name='simple_gen'),
            'Function/simple_gen'),
    (functools.partial(external_trace, library='lib', url='http://foo.com'),
            'External/foo.com/lib/'),
    (functools.partial(database_trace, 'select * from foo'),
            'Datastore/statement/None/foo/select'),
    (functools.partial(datastore_trace, 'lib', 'foo', 'bar'),
            'Datastore/statement/lib/foo/bar'),
    (functools.partial(message_trace, 'lib', 'op', 'typ', 'name'),
            'MessageBroker/lib/typ/op/Named/name'),
    (functools.partial(memcache_trace, 'cmd'),
            'Memcache/cmd'),
])
def test_awaitable_timing(trace, metric):

    @trace()
    async def coro():
        await asyncio.sleep(0.1)

    @background_task(name='test_awaitable')
    async def parent():
        await coro()

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics(
            'test_awaitable',
            background_task=True,
            scoped_metrics=[(metric, 1)],
            rollup_metrics=[(metric, 1)])
    def _test():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(parent())

    _test()

    # Check that coroutines time the total call time (including pauses)
    metric_key = (metric, '')
    assert full_metrics[metric_key].total_call_time >= 0.1


@pytest.mark.parametrize('trace,metric', [
    (functools.partial(function_trace, name='simple_gen'),
            'Function/simple_gen'),
    (functools.partial(external_trace, library='lib', url='http://foo.com'),
            'External/foo.com/lib/'),
    (functools.partial(database_trace, 'select * from foo'),
            'Datastore/statement/None/foo/select'),
    (functools.partial(datastore_trace, 'lib', 'foo', 'bar'),
            'Datastore/statement/lib/foo/bar'),
    (functools.partial(message_trace, 'lib', 'op', 'typ', 'name'),
            'MessageBroker/lib/typ/op/Named/name'),
    (functools.partial(memcache_trace, 'cmd'),
            'Memcache/cmd'),
])
@pytest.mark.parametrize('yield_from', [True, False])
@pytest.mark.parametrize('use_await', [True, False])
@pytest.mark.parametrize('coro_decorator_first', [True, False])
def test_asyncio_decorator_timing(trace, metric, yield_from,
        use_await, coro_decorator_first):

    if yield_from:
        def coro():
            yield from asyncio.sleep(0.1)
    else:
        def coro():
            time.sleep(0.1)

    if coro_decorator_first:
        coro = trace()(asyncio.coroutine(coro))
    else:
        coro = asyncio.coroutine(trace()(coro))

    if use_await:
        async def parent():
            await coro()
    else:
        @asyncio.coroutine
        def parent():
            yield from coro()

    parent = background_task(name='test_awaitable')(parent)

    metrics = []
    full_metrics = {}

    @capture_transaction_metrics(metrics, full_metrics)
    @validate_transaction_metrics(
            'test_awaitable',
            background_task=True,
            scoped_metrics=[(metric, 1)],
            rollup_metrics=[(metric, 1)])
    def _test():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(parent())

    _test()

    # Check that coroutines time the total call time (including pauses)
    metric_key = (metric, '')
    assert full_metrics[metric_key].total_call_time >= 0.1
