import tornado.ioloop
import tornado.web
import tornado.gen
import time

_has_web_asynchronous = hasattr(tornado.web, 'asynchronous')


class NativeSimpleHandler(tornado.web.RequestHandler):
    async def get(self, fast=False):
        if not fast:
            time.sleep(0.1)
        self.write("Hello, world")


if _has_web_asynchronous:
    class NativeWebAsyncHandler(tornado.web.RequestHandler):
        @tornado.web.asynchronous
        async def get(self, fast=False):
            io_loop = tornado.ioloop.IOLoop.current()
            io_loop.add_callback(self.done, fast=fast)

        async def done(self, fast):
            if not fast:
                time.sleep(0.1)
            self.write("Hello, world")
            self.finish()


if __name__ == "__main__":
    from _target_application import make_app
    app = make_app()
    app.listen(8888, address='127.0.0.1')
    tornado.ioloop.IOLoop.current().start()
