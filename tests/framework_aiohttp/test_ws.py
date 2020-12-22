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
from testing_support.fixtures import function_not_called

version_info = tuple(int(_) for _ in aiohttp.__version__.split('.')[:2])


@function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
def test_websocket(aiohttp_app):
    @asyncio.coroutine
    def ws_write():
        ws = yield from aiohttp_app.client.ws_connect('/ws')
        try:
            for _ in range(2):
                result = ws.send_str('Hello')
                if hasattr(result, '__await__'):
                    yield from result.__await__()
                msg = yield from ws.receive()
                assert msg.data == '/Hello'
        finally:
            yield from ws.close(code=1000)
            assert ws.close_code == 1000

    aiohttp_app.loop.run_until_complete(ws_write())
