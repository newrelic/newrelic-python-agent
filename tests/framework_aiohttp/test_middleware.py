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

import pytest
import asyncio
import aiohttp

from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings)

version_info = tuple(int(_) for _ in aiohttp.__version__.split('.')[:2])


@asyncio.coroutine
def middleware_factory(app, handler):

    @asyncio.coroutine
    def middleware_handler(request):
        response = yield from handler(request)
        return response

    return middleware_handler


middleware_tests = [
    (middleware_factory, 'Function/test_middleware:'
            'middleware_factory.<locals>.middleware_handler'),
]


if version_info >= (3, 0):
    @aiohttp.web.middleware
    @asyncio.coroutine
    def new_style_middleware(request, handler):
        response = yield from handler(request)
        return response

    middleware_tests.append(
        (new_style_middleware,
         'Function/test_middleware:new_style_middleware'),
    )


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('middleware,metric', middleware_tests)
def test_middleware(nr_enabled, aiohttp_app, middleware, metric):

    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request('GET', '/coro')
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text
        return resp

    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    if nr_enabled:
        scoped_metrics = [
            ('Function/_target_application:index', 1),
            (metric, 1),
        ]

        rollup_metrics = [
            ('Function/_target_application:index', 1),
            (metric, 1),
            ('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1),
        ]

        _test = validate_transaction_metrics('_target_application:index',
                scoped_metrics=scoped_metrics,
                rollup_metrics=rollup_metrics)(_test)
    else:
        settings = global_settings()

        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()
