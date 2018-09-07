import newrelic.api.web_transaction as web_transaction
from newrelic.core.transaction_cache import transaction_cache
from functools import partial
from benchmarks.util import (MockApplication, MockTrace, MockTransaction,
        MockTransactionCAT)
WebTransaction = web_transaction.WebTransaction
FunctionTrace = web_transaction.FunctionTrace


iterable = [b'Hello World']
ok = '200 OK'
headers = [('Content-Length', '0'), ('Content-Type', 'text/plain')]


def write(*args):
    pass


def start_response(*args):
    return write


def wsgi_application(environ, start_response):
    start_response(ok, headers)
    return iterable


class Lite(object):
    def setup(self, settings={
        'browser_monitoring.enabled': False,
    }):
        web_transaction.FunctionTrace = MockTrace
        web_transaction.WebTransaction = MockTransaction
        self.app = MockApplication(settings=settings)
        self.wrapped_app = partial(web_transaction.WSGIApplicationWrapper(
                wsgi_application,
                application=self.app,
        ), {}, start_response)

    def teardown(self):
        web_transaction.WebTransaction = WebTransaction
        web_transaction.FunctionTrace = FunctionTrace

    def time_wsgi_application_wrapper(self):
        self.wrapped_app()


class Framework(Lite):
    def setup(self):
        super(Framework, self).setup()
        self.wrapped_app = partial(web_transaction.WSGIApplicationWrapper(
                web_transaction.wsgi_application,
                application=self.app,
                framework=('cookies', 1),
        ), {}, start_response)


class AlreadyRunningTransaction(Framework):
    def setup(self):
        super(AlreadyRunningTransaction, self).setup()
        self.transaction = MockTransaction(self.app)

        self.transaction.thread_id = transaction_cache().current_thread_id()
        self.transaction.ignore_transaction = False
        self.transaction.save_transaction()

    def teardown(self):
        super(AlreadyRunningTransaction, self).setup()
        self.transaction.drop_transaction()


class CATResponse(Lite):
    def setup(self, settings={
        'browser_monitoring.enabled': False,
        'encoding_key': 'abcde',
    }):
        super(CATResponse, self).setup(settings=settings)
        web_transaction.WebTransaction = MockTransactionCAT
