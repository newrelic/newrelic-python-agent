from benchmarks.util import MockApplication, MockTransaction
from newrelic.api.wsgi_application import _WSGIApplicationMiddleware

html = b'<html><head></head><body></body></html>'
value = [html]
status = '200 OK'
response_headers_html = [
    ('Content-Type', 'text/html'), ('Content-Length', len(html))
]
response_headers_text = [('Content-Type', 'text/plain')]


def write(*args, **kwargs):
    pass


def start_response(*args, **kwargs):
    return write


def application_plain(environ, start_response):
    return value


class Base(object):

    params = ('html', 'text')
    param_names = ('content_type', )

    def setup(self, content_type):
        transaction = MockTransaction(MockApplication())
        self.middleware = _WSGIApplicationMiddleware(
                application_plain, None, start_response, transaction)

        if content_type == 'html':
            self.response_headers = response_headers_html
        else:
            self.response_headers = response_headers_text


class TimeStartResponse(Base):
    def time_start_response(self, content_type):
        self.middleware.start_response(status, self.response_headers)


class TimeIterable(Base):
    def setup(self, content_type):
        super(TimeIterable, self).setup(content_type)
        self.middleware.start_response(status, self.response_headers)

    def time_iterable(self, content_type):
        self.middleware.pass_through = False
        self.middleware.outer_write = None
        for _ in self.middleware:
            pass


class TimeInit(object):
    def setup(self):
        self.transaction = MockTransaction(MockApplication())

    def time_wsgi_application_middleware_init(self):
        _WSGIApplicationMiddleware(
                application_plain, None, start_response, self.transaction)
