import newrelic.api.wsgi_application as wsgi_application
from benchmarks.util import MockApplication, MockTrace, MockTransaction
FunctionTrace = wsgi_application.FunctionTrace
value = b'Hello World'


class Generator(object):
    def __iter__(self):
        return self

    def __next__(self):
        return value

    next = __next__

    def close(self):
        pass


class Suite(object):
    def setup(self):
        wsgi_application.FunctionTrace = MockTrace
        app = MockApplication()
        self.transaction = MockTransaction(app)
        self.iterable = wsgi_application._WSGIApplicationIterable(
                self.transaction, Generator())

    def teardown(self):
        wsgi_application.FunctionTrace = FunctionTrace

    def time_iterator(self):
        self.iterable.closed = False
        self.transaction._sent_start = None
        for _ in self.iterable:
            break

    def time_start_trace(self):
        self.iterable.response_trace = None
        self.transaction._sent_start = None
        self.iterable.start_trace()

    def time_close(self):
        self.iterable.closed = False
        self.iterable.close()
