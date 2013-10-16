import webtest
import threading
import time

import tornado.ioloop
import tornado.web
import tornado.wsgi

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("MAIN RESPONSE")

def wsgi_application(environ, start_response):
    status = '200 OK'
    output = 'WSGI RESPONSE'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

wsgi_application = tornado.wsgi.WSGIContainer(wsgi_application)

application = tornado.web.Application([
    (r"/main", MainHandler),
    (r"/wsgi", tornado.web.FallbackHandler, dict(fallback=wsgi_application)),
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

def test_mixed_application_main():
    response = test_application.get('/main')
    response.mustcontain('MAIN RESPONSE')

def test_mixed_application_wsgi():
    response = test_application.get('/wsgi')
    response.mustcontain('WSGI RESPONSE')
