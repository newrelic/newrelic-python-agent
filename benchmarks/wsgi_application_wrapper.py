import newrelic.api.web_transaction as web_transaction
from functools import partial
from benchmarks.util import MockApplication
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


class FakeTrace(object):
    def __init__(*args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass


class FakeTransaction(WebTransaction):
    def __init__(self, application, *args, **kwargs):
        self._state = WebTransaction.STATE_STOPPED
        self.stopped = False
        self.enabled = True
        self.current_node = None
        self.client_cross_process_id = None
        self._frameworks = set()
        self._name_priority = 0
        self._settings = application.settings

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass


class FakeTransactionCAT(FakeTransaction):
    def __init__(self, *args, **kwargs):
        super(FakeTransactionCAT, self).__init__(*args, **kwargs)
        self.client_cross_process_id = '1#1'
        self.queue_start = 0.0
        self.start_time = 0.0
        self.end_time = 0.0
        self._frozen_path = 'foobar'
        self._read_length = None
        self.guid = 'GUID'
        self.record_tt = False


class Lite(object):
    def setup(self, settings={
        'browser_monitoring.enabled': False,
    }):
        web_transaction.FunctionTrace = FakeTrace
        web_transaction.WebTransaction = FakeTransaction
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


class CATResponse(Lite):
    def setup(self, settings={
        'browser_monitoring.enabled': False,
        'encoding_key': 'abcde',
    }):
        super(CATResponse, self).setup(settings=settings)
        web_transaction.WebTransaction = FakeTransactionCAT
