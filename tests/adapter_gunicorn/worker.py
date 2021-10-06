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

from gunicorn.workers.sync import SyncWorker


class WsgiProxy(object):
    def __init__(self, asgi):
        self.asgi = asgi
        self.status_code = None
        self.headers = None
        self.iterable = []

    def __call__(self, environ, start_response):
        loop = asyncio.new_event_loop()
        instance = self.asgi({"type": "http"})
        loop.run_until_complete(instance(self.receive, self.send))
        start_response("200 OK", [])
        return [b"PONG"]

    async def send(self, message):
        pass

    async def receive(self):
        return {"type": "http.request"}


class AsgiWorker(SyncWorker):
    def handle_request(self, *args, **kwargs):
        asgi = self.wsgi
        self.wsgi = WsgiProxy(asgi)

        try:
            return super(AsgiWorker, self).handle_request(*args, **kwargs)
        finally:
            self.wsgi = asgi
