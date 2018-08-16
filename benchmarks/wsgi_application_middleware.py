from benchmarks.util import MockApplication, MockTransaction
from newrelic.api.web_transaction import _WSGIApplicationMiddleware
value = [b'<html><head></head><body></body></html>']
status = '200 OK'
response_headers_html = [('Content-Type', 'text/html'), ('Content-Length', len(value))]
response_headers_text = [('Content-Type', 'text/plain')]


def write(*args, **kwargs):
    pass


def start_response(*args, **kwargs):
    return write


def application_plain(environ, start_response):
    return value


class Base(object):
    def setup(self):
        transaction = MockTransaction(MockApplication())
        self.middleware = _WSGIApplicationMiddleware(
                application_plain, None, start_response, transaction)


class TimeMethods(Base):
    def time_start_response_html(self):
        self.middleware.start_response(status, response_headers_html)

    def time_start_response_plain(self):
        self.middleware.start_response(status, response_headers_text)


class TimePassThrough(Base):
    def setup(self):
        super(TimePassThrough, self).setup()
        self.middleware.start_response(status, response_headers_text)

    def time_pass_through(self):
        for _ in self.middleware:
            pass


class TimeHtmlInsertion(Base):
    def setup(self):
        super(TimeHtmlInsertion, self).setup()
        self.middleware.start_response(status, response_headers_html)

    def time_html_insertion(self):
        for _ in self.middleware:
            pass


class TimeInit(object):
    def setup(self):
        self.transaction = MockTransaction(MockApplication())

    def time_wsgi_application_middleware_init(self):
        _WSGIApplicationMiddleware(
                application_plain, None, start_response, self.transaction)
