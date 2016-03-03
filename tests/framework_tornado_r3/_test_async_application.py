import concurrent.futures
import functools
import socket
import tornado
import threading
import time

from newrelic.agent import current_transaction, function_trace
from newrelic.hooks.framework_tornado_r3.util import TransactionContext

from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPRequest
from tornado.web import Application, RequestHandler
from tornado.httpserver import HTTPServer
from tornado import stack_context
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.testing import bind_unused_port


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
    def get(self, error_location):
        self.location = error_location
        self.count = 0
        self.count = yield self.next_count()
        if self.location == '0':
            raise Tornado4TestException("location 0")

    def next_count(self):
        f = tornado.concurrent.Future()
        tornado.ioloop.IOLoop.current().add_callback(self._inc, f)
        if self.location == '1':
            raise Tornado4TestException("location 1")
        return f

    def _inc(self, f):
        f.set_result(self.count + 1)
        if self.location == '2':
            raise Tornado4TestException("location 2")

# This RequestHandler is equivalent to the RequestHandler above when
# location is set to 2. However, the testing framework exception handling seems
# to catch our exception unless we wrap in in asynchronous (which we shouldn't
# have to do) which prevents us from recording the exception.
class CoroutineException2RequestHandler(RequestHandler):
    RESPONSE = b'coroutine exception'

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self.count = 0
        self.count = yield self.next_count()

    def next_count(self):
        f = tornado.concurrent.Future()
        tornado.ioloop.IOLoop.current().add_callback(self._inc, f)
        return f

    def _inc(self, f):
        f.set_result(self.count + 1)
        raise Tornado4TestException("ERROR!")

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
        self.finish(self.RESPONSE)
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

class PrepareReturnsFutureHandler(RequestHandler):
    RESPONSE = b'preparedness'

    def prepare(self):
        f = tornado.concurrent.Future()
        tornado.ioloop.IOLoop.current().add_callback(self.resolve_future, f)
        return f

    def resolve_future(self, f):
        f.set_result(None)

    def get(self):
        self.write(self.RESPONSE)

class PrepareCoroutineReturnsFutureHandler(RequestHandler):
    RESPONSE = b'preparedness'

    @tornado.gen.coroutine
    def prepare(self):
        f = tornado.concurrent.Future()
        tornado.ioloop.IOLoop.current().add_callback(self.resolve_future, f)
        yield f

    def resolve_future(self, f):
        f.set_result(None)

    def get(self):
        self.write(self.RESPONSE)

class PrepareCoroutineFutureDoesNotResolveHandler(RequestHandler):
    RESPONSE = b'preparedness'

    @tornado.gen.coroutine
    def prepare(self):
        # Due to how Tornado works internally, since this coroutine returns a
        # future, it won't hang. It would hang if it were to yield the future.
        f = tornado.concurrent.Future()
        return f

    def get(self):
        self.write(self.RESPONSE)

class PrepareFinishesHandler(RequestHandler):
    RESPONSE = b'preparedness'

    def prepare(self):
        self.finish(self.RESPONSE)

    def get(self):
        # this should never get called
        pass

class OnFinishWithGetCoroutineHandler(RequestHandler):
    RESPONSE = b'get coroutine with on finish'

    @tornado.gen.coroutine
    def get(self):
        f = tornado.concurrent.Future()
        tornado.ioloop.IOLoop.current().add_callback(self.resolve_future, f)
        yield f
        self.write(self.RESPONSE)

    def resolve_future(self, f):
        f.set_result(None)

    def on_finish(self):
        pass

class AsyncFetchRequestHandler(RequestHandler):

    @tornado.web.asynchronous
    def get(self, request_type, port):
        url = 'http://localhost:%s' % port
        client = AsyncHTTPClient()
        # We test with a request object and a raw url as well as using the
        # callback as a positional argument and as a keyword argument.
        if request_type == 'requestobj':
            request = HTTPRequest(url)
            client.fetch(url, self.process_response)
        else:
            request = url
            client.fetch(url, callback=self.process_response)

    def process_response(self, response):
        self.finish(response.body)

class SyncFetchRequestHandler(RequestHandler):

    def get(self, request_type, port):
        url = 'http://localhost:%s' % port
        client = HTTPClient()

        # We test with a either request object or a raw url.
        if request_type == 'requestobj':
            request = HTTPRequest(url)
        else:
            request = url

        response = client.fetch(url)
        self.finish(response.body)

class RunSyncAddRequestHandler(RequestHandler):
    RESPONSE_TEMPLATE = 'The sum is %s'

    def __init__(self, *args, **kwargs):
        super(RunSyncAddRequestHandler, self).__init__(*args, **kwargs)
        # In versions prior to 4.2 there is no 'make_current' argument to
        # IOLoop. The behavior prior to 4.2 is identical to setting make_current
        # to False.
        if tornado.version < '4.2':
            self.my_io_loop = tornado.ioloop.IOLoop()
        else:
            self.my_io_loop = tornado.ioloop.IOLoop(make_current=False)

    def get(self, a, b):
        self.a = int(a)
        self.b = int(b)
        total = self.my_io_loop.run_sync(self.async_add)
        response = self.RESPONSE_TEMPLATE % total
        self.finish(response.encode('ascii'))

    def async_add(self):
        future = tornado.concurrent.Future()
        self.my_io_loop.add_callback(self.add, future)
        return future

    def add(self, future):
        self.total = self.a + self.b
        future.set_result(self.a + self.b)

    @classmethod
    def RESPONSE(cls, total):
        return (cls.RESPONSE_TEMPLATE % total).encode('ascii')

class ThreadScheduledCallbackRequestHandler(RequestHandler):
    RESPONSE = b'callback threading'

    def initialize(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(2)
        self.io_loop = tornado.ioloop.IOLoop.current()

    def get(self):
        self.schedule_thing()
        self.write(self.RESPONSE)

    @tornado.concurrent.run_on_executor
    def schedule_thing(self):
        self.io_loop.add_callback(self.do_thing)

    def do_thing(self):
        pass

class CallbackOnThreadExecutorRequestHandler(RequestHandler):
    RESPONSE = b'callback threading'

    def initialize(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(2)
        self.io_loop = tornado.ioloop.IOLoop.current()

    def get(self):
        tornado.ioloop.IOLoop.current().add_callback(self.do_thing)
        self.write(self.RESPONSE)

    @tornado.concurrent.run_on_executor
    def do_thing(self):
        pass

class ThreadScheduledCallAtRequestHandler(RequestHandler):
    RESPONSE = b'call_at threading'

    def initialize(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(2)
        self.io_loop = tornado.ioloop.IOLoop.current()

    def get(self):
        self.schedule_thing()
        self.write(self.RESPONSE)

    @tornado.concurrent.run_on_executor
    def schedule_thing(self):
        # call later calls call_at, but does the time math for you
        self.io_loop.call_later(0.1, self.do_thing)

    def do_thing(self):
        pass

class CallAtOnThreadExecutorRequestHandler(RequestHandler):
    RESPONSE = b'call_at threading'

    def initialize(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(2)
        self.io_loop = tornado.ioloop.IOLoop.current()

    def get(self):
        # call later calls call_at, but does the time math for you
        self.io_loop.call_later(0.1, self.do_thing)
        self.write(self.RESPONSE)

    @tornado.concurrent.run_on_executor
    def do_thing(self):
        pass

class AddFutureRequestHandler(RequestHandler):
    RESPONSE = b'Add future'

    def get(self):
        f = tornado.concurrent.Future()
        tornado.ioloop.IOLoop.current().add_future(f, self.do_thing)
        self.write(self.RESPONSE)

        # resolve the future asynchronously, after _execute here finishes
        tornado.ioloop.IOLoop.current().add_callback(f.set_result, (None,))

    def do_thing(self, future):
        pass

class AddDoneCallbackRequestHandler(RequestHandler):
    RESPONSE = b'Add future'

    def get(self):
        f = tornado.concurrent.Future()
        f.add_done_callback(lambda future: tornado.ioloop.IOLoop.current().add_callback(self.do_thing))
        self.write(self.RESPONSE)

        # resolve the future asynchronously, after _execute here finishes
        tornado.ioloop.IOLoop.current().add_callback(f.set_result, (None,))

    def do_thing(self):
        pass

@tornado.web.stream_request_body
class SimpleStreamingRequestHandler(RequestHandler):
    RESPONSE = b'streaming post'

    def data_received(self, chunk):
        pass

    def post(self):
        self.write(self.RESPONSE)

class SimpleThreadedFutureRequestHandler(RequestHandler):
    """This handler creates a future and passes it to a thread, which should
    resolve immediately, while the current method still has the transaction
    in the cache.
    """
    RESPONSE = b"please don't do this"

    def get(self, add_future=False):
        # Tornado futures are not thread safe, however that should not,
        # in itself, cause this test to fail because we do not access the future
        # from the main thread once we start the thread that we pass it to.
        f = tornado.concurrent.Future()

        add_future = (True if add_future == 'add_future' else False)

        if add_future:
            # When the future resolves, add a callback to the ioloop, wrapped
            # with a context that contains this transaction
            tornado.ioloop.IOLoop.current().add_future(f, self.do_stuff)
        else:
            # Add a callback to the future, which will be wrapped in
            # a context that contains this transaction, and will run in the
            # thread we pass the future to
            f.add_done_callback(self.do_stuff)

        # Resolve the future in a different thread, this will pass with it
        # the transaction piggy-backed on the callback inside the future
        t = threading.Thread(target=f.set_result, args=(None,))
        t.start()
        t.join()
        self.write(self.RESPONSE)

    def do_stuff(self, f=None):
         pass

class BusyWaitThreadedFutureRequestHandler(RequestHandler):
    """This handler creates a future and passes it to a thread, but with timing
    so that the callback from the future will likely be running when a callback
    from the main thread kicks in. We cannot absolutely guarantee that this
    will be the case, but there are assert statements in busy_wait that will
    fail and thus let us know if the timing was not as intended for this test
    case.
    """
    RESPONSE = b'bad programmer'

    def get(self, add_future=False):
        # Tornado futures are not thread safe, however that should not,
        # in itself, cause this test to fail because we do not access the future
        # from the main thread once we start the thread that we pass it to.
        f = tornado.concurrent.Future()

        self.add_future = (True if add_future == 'add_future' else False)

        if self.add_future:
            # When the future resolves, add a callback to the ioloop, wrapped
            # with a context that contains this transaction
            tornado.ioloop.IOLoop.current().add_future(f, self.long_wait)
        else:
            # Add a callback to the future, which will be wrapped in
            # a context that contains this transaction, and will run in the
            # thread we pass the future to
            f.add_done_callback(self.long_wait)

        self.write(self.RESPONSE)

        # Resolve the future in a different thread, this will pass with it
        # the transaction piggy-backed on the callback inside the future
        transaction = current_transaction()
        t = threading.Thread(target=self.resolve_future, args=(f, transaction))
        t.start()

        # Schedule a callback later that should be captured by the agent, the
        # goal is to run during the middle of the threaded callback
        tornado.ioloop.IOLoop.current().add_callback(self.do_stuff)

    def resolve_future(self, future, transaction):
        # Make sure that the get method has finished
        while not transaction._can_finalize:
            time.sleep(0.01)

        future.set_result(None)

    def long_wait(self, f=None):
        # We need this to take up enough time so that its likely to be "active"
        # when our main thread scheduled callback kicks in. If this is running
        # in a thread, as a result of add_done_callback, do_stuff should be able
        # to add and remove the transaction object from the cache *while* this
        # function is running. Otherwise, if this is running in the main thread
        # as a result of add_future, it will block do_stuff's ability to run,
        # and it will run on the IO loop after.

        assert not hasattr(self, 'stuff_done'), ('long_wait started before get '
                'method finished. Test timing incorrect, may need to re-run '
                'test')

        current_time = time.time()
        time.sleep(1)

        if self.add_future:
            assert not hasattr(self, 'stuff_done'), ('This should not be '
                    'possible since both long_wait and do_stuff are on the '
                    'ioloop, and the previous assert checked that it has not '
                    'ran. If this assert fails, just give up now.')
        else:
            assert hasattr(self, 'stuff_done'), ('do_stuff was not finished '
                    ' during long_wait. Test timing incorrect, may need to '
                    're-run test')

    @tornado.gen.coroutine
    def do_stuff(self):
        # Wait to run later, to come back during the middle of the threaded
        # callback (at least for the add_future case)
        yield tornado.gen.sleep(0.15)
        self.stuff_done = True

class CleanUpableRequestHandler(RequestHandler):

    CLEANUP = None

    def cleanup(self):
        if self.CLEANUP:
            self.CLEANUP()
            self.CLEANUP = None

    @classmethod
    def set_cleanup(cls, cleanup):
        """To be used by a test suite to inject a function into this handler.

        Argument:
          cleanup: A function to be called at the end of the request handler
            after the transaction closes. The handler should run this in a None
            transaction context after all other work is done. `cleanup` will
            only be invoked for 1 request. If one wants this to be called for
            subsequent requests, one must set this before each request."""
        cls.CLEANUP = cleanup

class AddDoneCallbackAddsCallbackRequestHandler(CleanUpableRequestHandler):
    """This adds a callback in an add_done_callback after the transaction
    completes. This should not increment/decrement the refcounter causing the
    transaction to finalize multiple times."""
    RESPONSE = b"Add done callback adds a callback."


    def get(self, future_type):
        if future_type == 'tornado':
            f = tornado.concurrent.Future()
        elif future_type == 'python':
            f = concurrent.futures.Future()
        else:
            # raise an error so the test fails
            raise Tornado4TestException("Bad url in test")

        f.add_done_callback(self.schedule_work)

        with TransactionContext(None):
            tornado.ioloop.IOLoop.current().add_callback(self.resolve_future, f)

        self.finish(self.RESPONSE)

    def resolve_future(self, f):
        f.set_result(None)

    def schedule_work(self, f):
        tornado.ioloop.IOLoop.current().add_callback(self.do_work)

    def do_work(self):
        with TransactionContext(None):
            tornado.ioloop.IOLoop.current().add_callback(self.cleanup)

class TransactionAwareFunctionAferFinalize(CleanUpableRequestHandler):
    RESPONSE = b'orphaned function'

    def get(self):
        self.write(self.RESPONSE)

        # Wrap the function up with this transaction

        func = stack_context.wrap(self.orphan)

        # But schedule it to run after the transaction has finalized by putting
        # it on the io_loop through a None context

        with TransactionContext(None):

            # place the call to the function inside a lambda so add_callback
            # here places its own stack context with None transaction around the
            # callback arg.

            tornado.ioloop.IOLoop.current().add_callback(lambda: func())

    def orphan(self):
        # Since the error we are testing for here is a log message, not a raised
        # Exception, we assert against the condition that would raise it when
        # this function finishes.

        transaction = current_transaction()
        assert transaction is None
        self.cleanup()

class AddCallbackFromSignalRequestHandler(RequestHandler):
    RESPONSE = b'ignore add_callback_from_signal'

    def get(self):
        self.write(self.RESPONSE)
        tornado.ioloop.IOLoop.current().add_callback_from_signal(self.do_thing)

    def do_thing(self):
        pass

class DoubleWrapRequestHandler(RequestHandler):
    RESPONSE = b'double wrap'

    def get(self):
        tornado.ioloop.IOLoop.current().add_callback(self.do_stuff)
        self.write(self.RESPONSE)

    @function_trace()
    def do_stuff(self):
        pass

class FutureDoubleWrapRequestHandler(RequestHandler):
    RESPONSE = b'future double wrap'

    @tornado.web.asynchronous
    def get(self, method):
        f = tornado.concurrent.Future()
        if method == 'add_done':
            f.add_done_callback(self.do_stuff)
        elif method == 'add_future':
            tornado.ioloop.IOLoop.current().add_future(f, self.do_stuff)

        tornado.ioloop.IOLoop.current().add_callback(self.resolve_future, f)

    def resolve_future(self, f):
        f.set_result(None)

    @function_trace()
    def do_stuff(self, future):
        self.finish(self.RESPONSE)


class RunnerRefCountRequestHandler(RequestHandler):
    """Verify that incrementing/decrementing the ref count in Runner will
    keep the transaction open until yielding from a coroutine completes.

    """

    RESPONSE = b'runner test'

    def initialize(self):
        self.io_loop = tornado.ioloop.IOLoop.current()
        self.result_future = tornado.concurrent.Future()

    def resolve(self, f):
        f.set_result('resolved!')

    @function_trace()
    def do_stuff(self):
        pass

    @tornado.gen.coroutine
    def coro(self):
        yield self.result_future

    @tornado.gen.coroutine
    def get(self):

        # Schedule future resolution after calling `yield self.coro()`

        with TransactionContext(None):
            self.io_loop.add_callback(self.resolve, self.result_future)

        result = yield self.coro()

        # If transaction closes prematurely, calling do_stuff() will
        # produce this error (because cache will have None):
        #
        #     "Attempt to add callback to ioloop with different
        #      transaction attached than in the cache."
        #
        # If transaction remains open (as it should), we can check for
        # the `do_stuff` metric to confirm it is in the transaction.

        self.do_stuff()
        self.write(self.RESPONSE)


class RunnerRefCountSyncGetRequestHandler(RunnerRefCountRequestHandler):
    """Verify that the transaction will be closed in coro() after the
    response is sent back. Since no transaction aware callbacks have been
    added to the IOLoop, we can see that decrementing the ref count to 0
    in Runner.run() is what causes the transaction to close.

    """

    RESPONSE = b'runner sync get test'

    @function_trace()
    def do_stuff(self):
        pass

    @tornado.gen.coroutine
    def coro(self):
        # Schedule future resolution after calling `yield self.result_future`

        with TransactionContext(None):
            self.io_loop.add_callback(self.resolve, self.result_future)

        result = yield self.result_future
        self.do_stuff()

    def get(self):
        result_future = self.coro()
        self.write(self.RESPONSE)


class RunnerRefCountErrorRequestHandler(RunnerRefCountRequestHandler):
    """Verify that the Runner ref count keeps the transaction open
    after the yield in get(), and that the error is recorded against
    the still open transaction.

    """

    RESPONSE = b'runner error test'

    @tornado.gen.coroutine
    def coro(self):
        yield self.result_future

    @tornado.gen.coroutine
    def get(self):
        with TransactionContext(None):
            self.io_loop.add_callback(self.resolve, self.result_future)

        result = yield self.coro()
        bad_divide = 1/0

        # Nothing beyond here gets called

        self.do_stuff()
        self.write(self.RESPONSE)


class IgnoreAddHandlerRequestHandler(RequestHandler):
    """Verify that handler functions added to the IOLoop during
    a transaction are not associated with the transaction.

    """

    RESPONSE = b'add handler'

    def initialize(self):
        listener, port = bind_unused_port()
        self.listener = listener
        self.port = port
        self.host = '127.0.0.1'
        self.io_loop = IOLoop.current()
        self.message = None

    def handle_message(self, fd, events):
        self.message = b'add handler'

    @tornado.gen.coroutine
    def send_message(self):
        stream = IOStream(socket.socket())

        yield stream.connect((self.host, self.port))
        yield stream.write(b'message')
        stream.close()

        raise tornado.gen.Return(None)

    @tornado.gen.coroutine
    def get(self):
        self.io_loop.add_handler(self.listener, self.handle_message,
                IOLoop.READ)

        yield self.send_message()
        assert self.message == self.RESPONSE

        self.write(self.message)

    def on_finish(self):
        self.io_loop.remove_handler(self.listener)

class NativeFuturesCoroutine(RequestHandler):

    RESPONSE = b'native future coroutine'
    NONE_RESPONSE = b'native future coroutine in None context'
    THREAD_RESPONSE = b'native future coroutine in thread'

    @tornado.gen.coroutine
    def get(self, resolve_method=None):

        f = concurrent.futures.Future()

        # Add a callback so we can check for it's metrics

        f.add_done_callback(self.do_thing)

        # Resolve the future outside the transaction - this would cause an
        # error if add_done_callback is not instrumented

        if resolve_method == 'thread':
            self.finish(self.THREAD_RESPONSE)

            t = threading.Thread(target=self.resolve, args=(f,))
            t.start()
        elif resolve_method == 'none-context':
            self.finish(self.NONE_RESPONSE)

            with TransactionContext(None):
                tornado.ioloop.IOLoop.current().add_callback(self.resolve, f)
        elif resolve_method is None:
            self.finish(self.RESPONSE)
            tornado.ioloop.IOLoop.current().add_callback(self.resolve, f)
        else:
            raise ValueError("Invalid future resolution method %s"
                    % resolve_method)

        yield f

    def resolve(self, f):
        f.add_done_callback(self.another_method)
        f.set_result(None)

    def do_thing(self, *args):
        pass

    def another_method(self, *args):
        pass

def get_tornado_app():
    return Application([
        ('/', HelloRequestHandler),
        ('/sleep', SleepRequestHandler),
        ('/one-callback', OneCallbackRequestHandler),
        ('/named-wrap-callback', NamedStackContextWrapRequestHandler),
        ('/multiple-callbacks', MultipleCallbacksRequestHandler),
        ('/sync-exception', SyncExceptionRequestHandler),
        ('/callback-exception', CallbackExceptionRequestHandler),
        ('/coroutine-exception/(\w+)', CoroutineExceptionRequestHandler),
        ('/coroutine-exception-2', CoroutineException2RequestHandler),
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
        ('/stream', SimpleStreamingRequestHandler),
        ('/async-fetch/(\w)+/(\d+)', AsyncFetchRequestHandler),
        ('/sync-fetch/(\w)+/(\d+)', SyncFetchRequestHandler),
        ('/run-sync-add/(\d+)/(\d+)', RunSyncAddRequestHandler),
        ('/prepare-future', PrepareReturnsFutureHandler),
        ('/prepare-coroutine', PrepareCoroutineReturnsFutureHandler),
        ('/prepare-unresolved', PrepareCoroutineFutureDoesNotResolveHandler),
        ('/prepare-finish', PrepareFinishesHandler),
        ('/on_finish-get-coroutine', OnFinishWithGetCoroutineHandler),
        ('/thread-scheduled-callback', ThreadScheduledCallbackRequestHandler),
        ('/thread-ran-callback', CallbackOnThreadExecutorRequestHandler),
        ('/thread-scheduled-call_at', ThreadScheduledCallAtRequestHandler),
        ('/thread-ran-call_at', CallAtOnThreadExecutorRequestHandler),
        ('/add-future', AddFutureRequestHandler),
        ('/add_done_callback', AddDoneCallbackRequestHandler),
        ('/future-thread/?(\w+)?', SimpleThreadedFutureRequestHandler),
        ('/future-thread-2/?(\w+)?', BusyWaitThreadedFutureRequestHandler),
        ('/add-done-callback/(\w+)', AddDoneCallbackAddsCallbackRequestHandler),
        ('/double-wrap', DoubleWrapRequestHandler),
        ('/done-callback-double-wrap/(\w+)', FutureDoubleWrapRequestHandler),
        ('/runner', RunnerRefCountRequestHandler),
        ('/runner-sync-get', RunnerRefCountSyncGetRequestHandler),
        ('/runner-error', RunnerRefCountErrorRequestHandler),
        ('/orphan', TransactionAwareFunctionAferFinalize),
        ('/add-handler-ignore', IgnoreAddHandlerRequestHandler),
        ('/signal-ignore', AddCallbackFromSignalRequestHandler),
        ('/native-future-coroutine/?([\w-]+)?', NativeFuturesCoroutine),
    ])
