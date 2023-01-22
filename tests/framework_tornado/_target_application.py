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

import time

import tornado.gen
import tornado.httpclient
import tornado.httputil
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.routing import PathMatches


def dummy(*args, **kwargs):
    pass


class BadGetStatusHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

    def get_status(self, *args, **kwargs):
        raise ValueError("Bad Status")


class ProcessCatHeadersHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, response_code=200, **kwargs):
        super(ProcessCatHeadersHandler, self).__init__(application, request, **kwargs)
        self.response_code = response_code

    def get(self, client_cross_process_id, txn_header, flush=None):
        import newrelic.api.transaction as _transaction

        txn = _transaction.current_transaction()
        if txn:
            txn._process_incoming_cat_headers(client_cross_process_id, txn_header)

        if self.response_code != 200:
            self.set_status(self.response_code)
            return

        self.write("Hello, world")

        if flush == "flush":
            # Force a flush prior to calling finish
            # This causes the headers to get written immediately. The tests
            # which hit this endpoint will check that the response has been
            # properly processed even though we send the headers here.
            self.flush()

            # change the headers to garbage
            self.set_header("Content-Type", "garbage")


class EchoHeaderHandler(tornado.web.RequestHandler):
    def get(self):
        response = str(self.request.headers.__dict__).encode("utf-8")
        self.write(response)


class SimpleHandler(tornado.web.RequestHandler):
    options = {"your_command": "options"}

    def get(self):
        self.write("Hello, world")

    def log_exception(self, *args, **kwargs):
        pass

    post = get
    put = get
    delete = get
    patch = get


class NativeSimpleHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write("Hello, world")


class SuperSimpleHandler(SimpleHandler):
    def get(self):
        super(SuperSimpleHandler, self).get()


class CallSimpleHandler(tornado.web.RequestHandler):
    def get(self):
        SimpleHandler(self.application, self.request).get()


class CoroThrowHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        try:
            yield self.throw_exception()
        except ValueError:
            pass
        self.write("Hello, world")

    @tornado.gen.coroutine
    def throw_exception(self):
        raise ValueError("Throwing exception.")


class CoroHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        yield tornado.gen.sleep(0)
        self.write("Hello, world")


class FakeCoroHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        self.write("Hello, world")


class InitializeHandler(tornado.web.RequestHandler):
    def initialize(self, *args, **kwargs):
        pass

    def get(self):
        self.write("Hello, world")


class HTMLInsertionHandler(tornado.web.RequestHandler):
    HTML = """<html>
    <head>
        <meta charset="utf-8">
        <title>My Website</title>
    </head>
    <body>
        Hello World! There is no New Relic Browser here :(
    </body>
    </html>
    """

    def get(self):
        self.finish(self.HTML)


class CrashHandler(tornado.web.RequestHandler):
    def get(self):
        raise ValueError("CrashHandler")


class MultiTraceHandler(tornado.web.RequestHandler):
    async def get(self):
        coros = (self.trace() for _ in range(2))
        await tornado.gen.multi(coros)
        self.write("*")

    def trace(self):
        from newrelic.api.function_trace import FunctionTrace

        with FunctionTrace(name="trace", terminal=True):
            pass


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def on_message(self, message):
        self.write_message("hello " + message)


class EnsureFutureHandler(tornado.web.RequestHandler):
    def get(self):
        import asyncio

        async def coro_trace():
            from newrelic.api.function_trace import FunctionTrace

            with FunctionTrace(name="trace", terminal=True):
                await tornado.gen.sleep(0)

        asyncio.ensure_future(coro_trace())


class WebNestedHandler(WebSocketHandler):
    def on_message(self, message):
        super(WebNestedHandler, self).on_message(message)


class CustomApplication(tornado.httputil.HTTPServerConnectionDelegate, tornado.httputil.HTTPMessageDelegate):
    def start_request(self, server_conn, http_conn):
        self.server_conn = server_conn
        self.http_conn = http_conn
        return self

    def finish(self):
        response_line = tornado.httputil.ResponseStartLine("HTTP/1.1", 200, "OK")
        headers = tornado.httputil.HTTPHeaders()
        headers["Content-Type"] = "text/plain"
        self.http_conn.write_headers(response_line, headers)
        self.http_conn.write(b"*")
        self.http_conn.finish()


class BlockingHandler(tornado.web.RequestHandler):
    total = 0
    future = None

    def initialize(self, yield_before_finish=False):
        self.yield_before_finish = yield_before_finish

    async def get(self, total=1):
        import asyncio

        total = int(total)

        cls = type(self)
        if cls.total == 0:
            cls.future = asyncio.Future()

        cls.total += 1
        if cls.total == total:
            cls.total = 0
            cls.future.set_result(True)
            cls.future = None
            time.sleep(0.1)
        else:
            await cls.future

        if self.yield_before_finish:
            await asyncio.sleep(0)

        self.write("*")


def make_app(custom=False):
    handlers = [
        (PathMatches(r"/simple"), SimpleHandler),
        (r"/crash", CrashHandler),
        (r"/call-simple", CallSimpleHandler),
        (r"/super-simple", SuperSimpleHandler),
        (r"/coro", CoroHandler),
        (r"/coro-throw", CoroThrowHandler),
        (r"/fake-coro", FakeCoroHandler),
        (r"/init", InitializeHandler),
        (r"/html-insertion", HTMLInsertionHandler),
        (r"/bad-get-status", BadGetStatusHandler),
        (r"/force-cat-response/(\S+)/(\S+)/(\S+)", ProcessCatHeadersHandler),
        (r"/304-cat-response/(\S+)/(\S+)", ProcessCatHeadersHandler, {"response_code": 304}),
        (r"/echo-headers", EchoHeaderHandler),
        (r"/native-simple", NativeSimpleHandler),
        (r"/multi-trace", MultiTraceHandler),
        (r"/web-socket", WebSocketHandler),
        (r"/ensure-future", EnsureFutureHandler),
        (r"/call-web-socket", WebNestedHandler),
        (r"/block/(\d+)", BlockingHandler),
        (r"/block-with-yield/(\d+)", BlockingHandler, {"yield_before_finish": True}),
    ]
    if custom:
        return CustomApplication()
    else:
        return tornado.web.Application(handlers, log_function=dummy)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888, address="127.0.0.1")
    tornado.ioloop.IOLoop.current().start()
