import aiohttp.wsgi
import asyncio
import mock

from gunicorn.workers import gaiohttp
from gunicorn.config import Config


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
