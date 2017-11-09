import sys
import tornado.ioloop
import tornado.web
import tornado.gen
import time


class SimpleHandler(tornado.web.RequestHandler):
    def get(self, fast=False):
        if not fast:
            time.sleep(0.1)
        self.write("Hello, world")


class OnFinishHandler(SimpleHandler):
    def on_finish(self):
        time.sleep(0.1)


class CoroThrowHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self, fast=False):
        if not fast:
            yield tornado.gen.sleep(0.1)
        try:
            yield self.boom()
        except ValueError:
            pass
        self.write("Hello, world")

    @tornado.gen.coroutine
    def boom(self):
        raise ValueError('BOOM!')


class CoroHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self, fast=False):
        if not fast:
            yield tornado.gen.sleep(0.1)
        self.write("Hello, world")


class FakeCoroHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self, fast=False):
        if not fast:
            time.sleep(0.1)
        self.write("Hello, world")


class WebAsyncHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, fast=False):
        io_loop = tornado.ioloop.IOLoop.current()
        io_loop.add_callback(self.done, fast=fast)

    def done(self, fast):
        if not fast:
            time.sleep(0.1)
        self.write("Hello, world")
        self.finish()


class InitializeHandler(tornado.web.RequestHandler):
    def initialize(self, *args, **kwargs):
        time.sleep(0.1)

    def get(self, fast=False):
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


def make_app():
    handlers = [
        (r'/simple(/.*)?', SimpleHandler),
        (r'/coro(/.*)?', CoroHandler),
        (r'/coro-throw(/.*)?', CoroThrowHandler),
        (r'/fake-coro(/.*)?', FakeCoroHandler),
        (r'/web-async(/.*)?', WebAsyncHandler),
        (r'/init(/.*)?', InitializeHandler),
        (r'/html-insertion', HTMLInsertionHandler),
        (r'/on-finish(/.*)?', OnFinishHandler),
    ]
    if sys.version_info >= (3, 5):
        from _target_application_native import (NativeSimpleHandler,
                NativeWebAsyncHandler)
        handlers.extend([
            (r'/native-simple(/.*)?', NativeSimpleHandler),
            (r'/native-web-async(/.*)?', NativeWebAsyncHandler),
        ])
    return tornado.web.Application(handlers)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888, address='127.0.0.1')
    tornado.ioloop.IOLoop.current().start()
