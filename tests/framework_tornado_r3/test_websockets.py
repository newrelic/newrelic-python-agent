import sys

import pytest

try:
    import asyncio
except ImportError:
    asyncio = None

import tornado.gen
import tornado.testing
import tornado.web

from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect, WebSocketHandler

from tornado_fixtures import (tornado_validate_transaction_cache_empty,
        tornado_validate_errors)

from testing_support.fixtures import function_not_called

if sys.version_info >= (2, 7):
    from zmq.eventloop.ioloop import ZMQIOLoop


class BaseWebSocketsHandler(WebSocketHandler):

    def initialize(self, close_future):
        self.close_future = close_future

    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))


class BaseWebSocketsTest(tornado.testing.AsyncHTTPTestCase):

    # Starting with Tornado 5, when available it will use the asyncio event
    # loop. If this is the case, override and force use of the tornado event
    # loop. The asyncio event loop will be tested separately.

    if IOLoop.configurable_default().__name__ == 'AsyncIOLoop':
        def get_new_ioloop(self):
            IOLoop.configure('tornado.ioloop.PollIOLoop')
            return IOLoop.current()

    def get_protocol(self):
        return 'ws'

    @tornado.gen.coroutine
    def ws_connect(self, url):
        ws = yield websocket_connect(url)
        raise tornado.gen.Return(ws)

    @tornado.gen.coroutine
    def close(self, ws):
        ws.close()
        yield self.close_future


class BaseWebSocketsZmqTest(BaseWebSocketsTest):
    def get_new_ioloop(self):
        return ZMQIOLoop()


class BaseWebSocketsAsyncIOTest(BaseWebSocketsTest):
    def get_new_ioloop(self):
        IOLoop.configure('tornado.platform.asyncio.AsyncIOLoop')
        return IOLoop()


class HelloHandler(BaseWebSocketsHandler):

    def on_message(self, message):
        self.write_message(b'hello', binary=True)


class AllTests(object):

    def get_app(self):
        self.close_future = tornado.gen.Future()
        return tornado.web.Application([
            ('/', HelloHandler, {'close_future': self.close_future}),
        ])

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(expect_transaction=False)
    @function_not_called('newrelic.api.transaction', 'Transaction.__init__')
    @tornado.testing.gen_test
    def test_no_transaction_no_errors(self):
        url = self.get_url('/')
        ws = yield self.ws_connect(url)
        result = ws.write_message('foo')

        # For Tornado >= 4.3, result is a future.
        if result:
            yield result

        response = yield ws.read_message()
        self.assertEqual(response, b'hello')

        yield self.close(ws)


class TornadoWebSocketsPollIOLoopTest(AllTests, BaseWebSocketsTest):
    pass


@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class TornadoWebSocketsZmqIOLoopTest(AllTests, BaseWebSocketsZmqTest):
    pass


@pytest.mark.skipif(not asyncio, reason='No asyncio module available')
class TornadoWebsocketsAsyncIOLoopTest(AllTests,
        BaseWebSocketsAsyncIOTest):
    pass
