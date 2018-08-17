import newrelic.api.web_transaction as web_transaction
from benchmarks.util import MockApplication, MockTrace, MockTransaction
FunctionTrace = web_transaction.FunctionTrace
value = b'Hello World'


class Generator(object):
    def __iter__(self):
        return self

    def __next__(self):
        return value

    def close(self):
        pass


class Suite(object):
    def setup(self):
        web_transaction.FunctionTrace = MockTrace
        app = MockApplication()
        self.transaction = MockTransaction(app)
        self.iterable = web_transaction._WSGIApplicationIterable(
                self.transaction, Generator())

    def teardown(self):
        web_transaction.FunctionTrace = FunctionTrace

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
