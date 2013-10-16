import webtest
import threading
import time

import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("MAIN RESPONSE")

application = tornado.web.Application([
    (r"/main", MainHandler),
])

server_thread = None
server_ready = threading.Event()

def setup_module(module):
    global server_thread

    def run():
        application.listen(8888)
        server_ready.set()
        tornado.ioloop.IOLoop.instance().start()

    server_thread = threading.Thread(target=run)
    server_thread.start()
    server_ready.wait()

def teardown_module(module):
    tornado.ioloop.IOLoop.instance().stop()
    server_thread.join()

test_application = webtest.TestApp('http://localhost:8888')

def test_async_application_main():
    response = test_application.get('/main')
    response.mustcontain('MAIN RESPONSE')
