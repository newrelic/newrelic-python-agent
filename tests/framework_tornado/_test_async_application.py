import time

import tornado
import tornado.web
import tornado.wsgi
import tornado.ioloop
import tornado.gen

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('MAIN RESPONSE')
    def post(self):
        self.write('MAIN RESPONSE')

class DelayHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        tornado.ioloop.IOLoop.instance().add_timeout(time.time()+0.1,self.delayed)
        self.write('DELAY RESPONSE')
    def delayed(self):
        self.finish()

class EngineHandler(tornado.web.RequestHandler):
    @tornado.gen.engine
    def get(self):
        result = yield tornado.gen.Task(self.callback)
        self.write(result)
    def callback(self, callback):
        time.sleep(0.1)
        callback('DELAY RESPONSE')

if tornado.version_info[:2] >= (3, 0):
    class CoroutineHandler(tornado.web.RequestHandler):
        @tornado.gen.coroutine
        def get(self):
            result = yield tornado.gen.Task(self.callback)
            self.write(result)
        def callback(self, callback):
            time.sleep(0.1)
            callback('DELAY RESPONSE')
else:
    CoroutineHandler = EngineHandler

class Raise404Handler(tornado.web.RequestHandler):
    def get(self):
        raise tornado.web.HTTPError(404)

def wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'WSGI RESPONSE'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

wsgi_application = tornado.wsgi.WSGIContainer(wsgi_application)

application = tornado.web.Application([
    (r'/main', MainHandler),
    (r'/delay', DelayHandler),
    (r'/engine', EngineHandler),
    (r'/coroutine', CoroutineHandler),
    (r'/raise404', Raise404Handler),
    (r'/wsgi', tornado.web.FallbackHandler, dict(fallback=wsgi_application)),
])
