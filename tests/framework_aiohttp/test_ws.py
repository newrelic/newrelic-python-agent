import asyncio
from testing_support.fixtures import function_not_called


@function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
def test_websocket(aiohttp_app):

    @asyncio.coroutine
    def ws_write():
        ws = yield from aiohttp_app.client.ws_connect('/ws')
        try:
            for _ in range(2):
                ws.send_str('Hello')
                msg = yield from ws.receive()
                assert msg.data == '/Hello'
        finally:
            yield from ws.close(code=1000)
            assert ws.close_code == 1000

    aiohttp_app.loop.run_until_complete(ws_write())
