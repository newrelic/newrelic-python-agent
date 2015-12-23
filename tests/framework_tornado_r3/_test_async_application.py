import functools
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

    @tornado.web.asynchronous
    def head(self):
        self.set_status(200)
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    @tornado.web.asynchronous
    def post(self):
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    @tornado.web.asynchronous
    def delete(self):
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    @tornado.web.asynchronous
    def patch(self):
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    @tornado.web.asynchronous
    def put(self):
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    @tornado.web.asynchronous
    def options(self):
        tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    def finish_callback(self):
        self.finish(self.RESPONSE)

class NamedStackContextWrapRequestHandler(RequestHandler):
    RESPONSE = b'another callback'

    @tornado.web.asynchronous
    def get(self):
        # stackcontext.wrap will not re-wrap an already wrapped callback,
        # so this allows us to test that we can extract the callback, if it
        # is used as a keyword arg.
        tornado.ioloop.IOLoop.current().add_callback(
                tornado.stack_context.wrap(fn=self.finish_callback))

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

class SyncExceptionRequestHandler(RequestHandler):
    RESPONSE = b'sync exception'

    def get(self):
        divide = 10/0  # exception
        self.write(self.RESPONSE)  # never executed

class CallbackExceptionRequestHandler(RequestHandler):
    RESPONSE = b'callback exception'
    _MAX_COUNTER = 5

    @tornado.web.asynchronous
    def get(self):
        tornado.ioloop.IOLoop.current().add_callback(self.counter_callback, 1)

    def counter_callback(self, counter):
        if counter < self._MAX_COUNTER:
            tornado.ioloop.IOLoop.current().add_callback(
                self.counter_callback, counter+1)
        elif count == 3:  # exception since count (vs counter) is not defined
            pass
        else:
            tornado.ioloop.IOLoop.current().add_callback(self.finish_callback)

    def finish_callback(self):
        self.finish(self.RESPONSE)

class CoroutineExceptionRequestHandler(RequestHandler):
    RESPONSE = b'coroutine exception'

    @tornado.gen.coroutine
    def get(self):
        # Scheduling on_finish is a hack that is needed because we require
        # on_finish to be called to close the transaction. When an exception is
        # thrown here on_finish will not be scheduled on the IOLoop causing us
        # to timeout in the tests (though checking manually the correct
        # transaction is written). The mechanism for exiting a transaction will
        # change and when it does we should remove this manual scheduling of
        # on_finish. See PYTHON-1707.
        tornado.ioloop.IOLoop.current().add_callback(self.on_finish)
        raise tornado.gen.BadYieldError
        self.finish(self.RESPONSE)  # This will never be called.

# This isn't really an exception but a legitimate way to end request handling.
class FinishExceptionRequestHandler(RequestHandler):
    RESPONSE = b'Finish'

    def get(self):
        self.write(self.RESPONSE)
        raise tornado.web.Finish()

class ReturnExceptionRequestHandler(RequestHandler):
    RESPONSE_TEMPLATE = u'Return %s'
    RESPONSE = b'Return 1'  # 1 is the output from self.one()

    @tornado.gen.coroutine
    def get(self):
        x = yield self.one()
        response = self.RESPONSE_TEMPLATE % x
        self.finish(response.encode('ascii'))

    # This really isn't an exception but the standard with to return from a
    # coroutine.
    @tornado.gen.coroutine
    def one(self):
        raise tornado.gen.Return(1)

class DivideRequestHandler(RequestHandler):
    RESPONSE = u'Division %s / %s = %s'

    def divide(self, a, b, immediate):
        f = tornado.concurrent.Future()

        if immediate:
            # Set future result immediately. In this case we never need to
            # call run on the tornado.gen.Runner object and the coroutine isn't
            # really asynchronous.
            f.set_result(a/b)
        else:
            # We add a callback to do the division. In this case we are in a
            # coroutine which actually run asynchronously.
            tornado.ioloop.IOLoop.current().add_callback(self._divide, f, a, b)

        return f

    def _divide(self, future, a, b):
        future.set_result(a/b)

class IOLoopDivideRequestHandler(DivideRequestHandler):

    @tornado.gen.coroutine
    def get(self, a, b, immediate=False):
        a = float(a)
        b = float(b)
        immediate = (True if immediate == 'immediate' else False)
        quotient = yield self.divide(a, b, immediate=immediate)
        response = self.RESPONSE % (a, b, quotient)
        self.finish(response.encode('ascii'))

class EngineDivideRequestHandler(DivideRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, a, b, immediate=False):
        a = float(a)
        b = float(b)
        immediate = (True if immediate == 'immediate' else False)
        quotient = yield self.divide(a, b, immediate=immediate)
        response = self.RESPONSE % (a, b, quotient)
        self.finish(response.encode('ascii'))

class NestedCoroutineDivideRequestHandler(DivideRequestHandler):

    @tornado.gen.coroutine
    def get(self, a, b):
        a = float(a)
        b = float(b)
        yield self.do_divide(a, b)
        response = self.RESPONSE % (a, b,  self.quotient)
        self.finish(response.encode('ascii'))

    @tornado.gen.coroutine
    def do_divide(self, a, b):
        self.quotient = yield self.divide(a, b, False)

class ReturnFirstDivideRequestHandler(DivideRequestHandler):
    RESPONSE = b"Return immediately"

    @tornado.gen.coroutine
    def get(self, a, b):
        self.finish(self.RESPONSE.encode('ascii'))
        a = float(a)
        b = float(b)
        yield self.do_divide(a, b)

    @tornado.gen.coroutine
    def do_divide(self, a, b):
        self.quotient = yield self.divide(a, b, False)

class CallLaterRequestHandler(RequestHandler):
    RESPONSE = b"Return immediately"

    def get(self, cancel=False):
        self.finish(self.RESPONSE)
        timeout = tornado.ioloop.IOLoop.current().call_later(0.005, self.later)

        cancel = (True if cancel == 'cancel' else False)
        if cancel:

            # first call to cancel will decrement counter, second should be
            # ignored

            tornado.ioloop.IOLoop.current().remove_timeout(timeout)
            tornado.ioloop.IOLoop.current().remove_timeout(timeout)

    def later(self):
        pass

class CancelAfterRanCallLaterRequestHandler(RequestHandler):
    RESPONSE = b"Return immediately"

    @tornado.gen.coroutine
    def get(self):
        self.finish(self.RESPONSE)
        timeout = tornado.ioloop.IOLoop.current().call_later(0.005, self.later)
        yield tornado.gen.sleep(0.01)
        tornado.ioloop.IOLoop.current().remove_timeout(timeout)

    def later(self):
        pass

class PrepareOnFinishRequestHandler(RequestHandler):
    RESPONSE = b'bookend get'

    def prepare(self):
        pass

    def get(self):
        self.finish(self.RESPONSE)

    def on_finish(self):
        pass

class PrepareOnFinishRequestHandlerSubclass(PrepareOnFinishRequestHandler):
    def get(self):
        self.finish(self.RESPONSE)

def get_tornado_app():
    return Application([
        ('/', HelloRequestHandler),
        ('/sleep', SleepRequestHandler),
        ('/one-callback', OneCallbackRequestHandler),
        ('/named-wrap-callback', NamedStackContextWrapRequestHandler),
        ('/multiple-callbacks', MultipleCallbacksRequestHandler),
        ('/sync-exception', SyncExceptionRequestHandler),
        ('/callback-exception', CallbackExceptionRequestHandler),
        ('/coroutine-exception', CoroutineExceptionRequestHandler),
        ('/finish-exception', FinishExceptionRequestHandler),
        ('/return-exception', ReturnExceptionRequestHandler),
        ('/ioloop-divide/(\d+)/(\d+)/?(\w+)?', IOLoopDivideRequestHandler),
        ('/engine-divide/(\d+)/(\d+)/?(\w+)?', EngineDivideRequestHandler),
        ('/nested-divide/(\d+)/(\d+)/?', NestedCoroutineDivideRequestHandler),
        ('/return-divide/(\d+)/(\d+)/?', ReturnFirstDivideRequestHandler),
        ('/call-at/?(\w+)?', CallLaterRequestHandler),
        ('/cancel-timer', CancelAfterRanCallLaterRequestHandler),
        ('/bookend', PrepareOnFinishRequestHandler),
        ('/bookend-subclass', PrepareOnFinishRequestHandlerSubclass),
    ])
