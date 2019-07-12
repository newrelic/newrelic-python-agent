import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.httpclient
import tornado.websocket


def dummy(*args, **kwargs):
    pass


class BadGetStatusHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

    def get_status(self, *args, **kwargs):
        raise ValueError("OOPS")


class ProcessCatHeadersHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, response_code=200, **kwargs):
        super(ProcessCatHeadersHandler, self).__init__(application, request,
                **kwargs)
        self.response_code = response_code

    def get(self, client_cross_process_id, txn_header, flush=None):
        import newrelic.api.transaction as _transaction
        txn = _transaction.current_transaction()
        if txn:
            txn._process_incoming_cat_headers(client_cross_process_id,
                    txn_header)

        if self.response_code != 200:
            self.set_status(self.response_code)
            return

        self.write("Hello, world")

        if flush == 'flush':
            # Force a flush prior to calling finish
            # This causes the headers to get written immediately. The tests
            # which hit this endpoint will check that the response has been
            # properly processed even though we send the headers here.
            self.flush()

            # change the headers to garbage
            self.set_header('Content-Type', 'garbage')


class EchoHeaderHandler(tornado.web.RequestHandler):
    def get(self):
        response = str(self.request.headers.__dict__).encode('utf-8')
        self.write(response)


class SimpleHandler(tornado.web.RequestHandler):
    options = {'your_command': 'options'}

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


class CallSimpleHandler(tornado.web.RequestHandler):
    def get(self):
        SimpleHandler(self.application, self.request).get()


class CoroThrowHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
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


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def on_message(self, message):
        self.write_message("hello " + message)


def make_app():
    handlers = [
        (r'/simple', SimpleHandler),
        (r'/call-simple', CallSimpleHandler),
        (r'/coro', CoroHandler),
        (r'/coro-throw', CoroThrowHandler),
        (r'/fake-coro', FakeCoroHandler),
        (r'/init', InitializeHandler),
        (r'/html-insertion', HTMLInsertionHandler),
        (r'/bad-get-status', BadGetStatusHandler),
        (r'/force-cat-response/(\S+)/(\S+)/(\S+)', ProcessCatHeadersHandler),
        (r'/304-cat-response/(\S+)/(\S+)', ProcessCatHeadersHandler,
                {'response_code': 304}),
        (r'/echo-headers', EchoHeaderHandler),
        (r'/native-simple', NativeSimpleHandler),
        (r'/web-socket', WebSocketHandler),
    ]
    return tornado.web.Application(handlers, log_function=dummy)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888, address='127.0.0.1')
    tornado.ioloop.IOLoop.current().start()
