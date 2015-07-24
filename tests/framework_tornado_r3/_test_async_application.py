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

class TestServer(threading.Thread):
    def __init__(self, http_port=8000):
        super(TestServer, self).__init__()
        self.http_server = None
        self.application = None
        self.http_port = http_port
        self.server_ready = threading.Event()

    def run(self):
        self.application = Application([
            ('/', HelloRequestHandler),
            ('/sleep', SleepRequestHandler),
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

test_server = None
def get_url(path=''):
    return test_server.get_url(path)

def setup_application_server():
    @function_wrapper
    def _setup_application_server(wrapped, instance, args, kwargs):
        global test_server
        test_server = TestServer()
        test_server.start()
        try:
            # threading.Event.wait() always returns None in py2.6 instead of a
            # boolean as in >= py2.7. So we don't check the return value and
            # check threading.Event.is_set() instead.
            test_server.server_ready.wait(10.0)
            if not test_server.server_ready.is_set():
                raise Tornado4TestException('Application test server could not start.')
            wrapped(*args, **kwargs)
        finally:
            test_server.stop_server()
    return _setup_application_server

class TestClient(threading.Thread):
    def __init__(self, url):
        super(TestClient, self).__init__()
        self.url = url
        self.response = None

    def run(self):
        client = HTTPClient()
        self.response = client.fetch(self.url)
        client.close()
