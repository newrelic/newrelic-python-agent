import aiohttp.wsgi
import asyncio
import mock
import pytest
import socket

from aiohttp.protocol import RawRequestMessage, HttpVersion
from aiohttp.streams import EmptyStreamReader
from gunicorn.workers import gaiohttp
from gunicorn.config import Config
from multidict import CIMultiDict
from _test_application import get_application


def create_server(app, loop=None):

    sockets = socket.getaddrinfo('127.0.0.1', '8080')
    timeout = 60
    config = Config()
    log = mock.Mock()

    if loop is None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    worker = gaiohttp.AiohttpWorker('age', 'ppid', sockets, app,
            timeout, config, log)
    worker.loop = loop

    return worker


def _get_message():
    # TODO: Should be moved further out so this is handled automatically
    # through HttpRequestParser.
    headers = CIMultiDict()
    headers.add('Host', 'localhost:8080')
    headers.add('Accept', '*/*')
    return RawRequestMessage(method='GET', path='/ping',
            version=HttpVersion(major=1, minor=1), headers=headers,
            raw_headers=[(bytearray(b'HOST'), bytearray(b'localhost:8000')),
            (bytearray(b'USER-AGENT')), (bytearray(b'ACCEPT'),
            bytearray(b'*/*'))], should_close=False, compression=None)


@pytest.mark.parametrize('nr_enabled', [True, False])
def test_valid_response(nr_enabled):

    def _test():
        wsgi_app = get_application()
        server = create_server(wsgi_app)
        factory = server.factory(wsgi_app, ('127.0.0.1', '8080'))
        message = _get_message()
        payload = EmptyStreamReader()
        server.loop.run_until_complete(factory.handle_request(message, payload))

    _test()
