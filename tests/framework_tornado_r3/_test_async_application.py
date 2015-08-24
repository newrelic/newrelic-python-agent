import threading
import tornado

from newrelic.agent import function_wrapper

from tornado.httpclient import HTTPClient
from tornado.web import Application, RequestHandler
from tornado.httpserver import HTTPServer

class Tornado4TestException(Exception):
    pass

class HelloRequestHandler(RequestHandler):
    RESPONSE = b'Hello, world.'

    def get(self):
        self.write(self.RESPONSE)

class SleepRequestHandler(RequestHandler):
    RESPONSE = b'sleep'

    @tornado.gen.coroutine
    def get(self):
        yield tornado.gen.sleep(2)
        self.finish(self.RESPONSE)

class OneCallbackRequestHandler(RequestHandler):
    RESPONSE = b'one callback'

    @tornado.web.asynchronous
    def get(self):
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    def finish_callback(self):
        self.finish(self.RESPONSE)

class MultipleCallbacksRequestHandler(RequestHandler):
    RESPONSE = b'multiple callbacks'
    _MAX_COUNTER = 2

    @tornado.web.asynchronous
    def get(self):
        tornado.ioloop.IOLoop.current().add_callback(self.counter_callback, 1)

    def counter_callback(self, counter):
        if counter < self._MAX_COUNTER:
            tornado.ioloop.IOLoop.current().add_callback(
                    self.counter_callback, counter+1)
        else:
            tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    def finish_callback(self):
        self.finish(self.RESPONSE)

DEFAULT_HTTP_PORT = 2456

class TestServer(threading.Thread):
    def __init__(self, http_port=DEFAULT_HTTP_PORT):
        super(TestServer, self).__init__()
        self.http_server = None
        self.application = None
        self.http_port = http_port
        self.server_ready = threading.Event()

    def run(self):
        self.application = Application([
            ('/', HelloRequestHandler),
            ('/sleep', SleepRequestHandler),
            ('/one-callback', OneCallbackRequestHandler),
            ('/multiple-callbacks', MultipleCallbacksRequestHandler),
            ])
        self.http_server = HTTPServer(self.application)
        self.http_server.listen(self.http_port, '')
        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_callback(self.server_ready.set)
        ioloop.start()

    # The following methods are intended to be called from different thread than
    # the running TestServer thread.
    def get_url(self, path=''):
        return 'http://localhost:%s/%s' % (self.http_port, path)

    def stop_server(self):
        self.http_server.stop()
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.add_callback(ioloop.stop)
        self.join()

class TestClient(threading.Thread):
    def __init__(self, url):
        super(TestClient, self).__init__()
        self.url = url
        self.response = None

    def run(self):
        client = HTTPClient()
        self.response = client.fetch(self.url)
        client.close()
