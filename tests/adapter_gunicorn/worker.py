import asyncio
from gunicorn.workers.sync import SyncWorker


class WsgiProxy(object):
    def __init__(self, asgi):
        self.asgi = asgi
        self.status_code = None
        self.headers = None
        self.iterable = []

    def __call__(self, environ, start_response):
        loop = asyncio.get_event_loop()
        instance = self.asgi({'type': 'http'})
        loop.run_until_complete(instance(self.receive, self.send))
        start_response('200 OK', [])
        return [b'PONG']

    @asyncio.coroutine
    def send(self, message):
        pass

    @asyncio.coroutine
    def receive(self):
        return {'type': 'http.request'}


class AsgiWorker(SyncWorker):
    def handle_request(self, *args, **kwargs):
        asgi = self.wsgi
        self.wsgi = WsgiProxy(asgi)

        try:
            return super(AsgiWorker, self).handle_request(*args, **kwargs)
        finally:
            self.wsgi = asgi
