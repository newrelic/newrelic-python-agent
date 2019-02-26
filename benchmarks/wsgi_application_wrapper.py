import newrelic.api.wsgi_application as wsgi_application
from newrelic.core.transaction_cache import transaction_cache
from functools import partial
from benchmarks.util import (MockApplication, MockTrace, MockTransaction,
        MockTransactionCAT)
WebTransaction = wsgi_application.WebTransaction
FunctionTrace = wsgi_application.FunctionTrace


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
        wsgi_application.FunctionTrace = MockTrace
        wsgi_application.WebTransaction = MockTransaction
        self.app = MockApplication(settings=settings)
        self.wrapped_app = partial(wsgi_application.WSGIApplicationWrapper(
                wsgi_application,
                application=self.app,
        ), {}, start_response)

    def teardown(self):
        wsgi_application.WebTransaction = WebTransaction
        wsgi_application.FunctionTrace = FunctionTrace

    def time_wsgi_application_wrapper(self):
        self.wrapped_app()


class Framework(Lite):
    def setup(self):
        super(Framework, self).setup()
        self.wrapped_app = partial(wsgi_application.WSGIApplicationWrapper(
                wsgi_application.wsgi_application,
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
        wsgi_application.WebTransaction = MockTransactionCAT
