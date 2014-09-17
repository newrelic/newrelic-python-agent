import pytest

import webtest
import threading

import tornado
import tornado.ioloop

from newrelic.packages import six

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, raise_background_exceptions)

from newrelic.agent import function_wrapper

def wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'WSGI RESPONSE'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

server_thread = None
server_ready = threading.Event()

@function_wrapper
def setup_application_server(wrapped, instance, args, kwargs):
    global server_thread

    def run():
        import tornado.web
        import tornado.wsgi
        import tornado.httpserver

        wsgi_container = tornado.wsgi.WSGIContainer(wsgi_application)

        http_server = tornado.httpserver.HTTPServer(wsgi_container)
        http_server.listen(8890)
        server_ready.set()
        tornado.ioloop.IOLoop.instance().start()

    if server_thread is None:
        server_thread = threading.Thread(target=run)
        server_thread.start()
        server_ready.wait(10.0)

    return wrapped(*args, **kwargs)

def teardown_module(module):
    global server_thread

    tornado.ioloop.IOLoop.instance().stop()
    if server_thread is not None:
        server_thread.join()

_test_application = webtest.TestApp('http://localhost:8890')

_test_wsgi_http_server_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/test_wsgi_http_server:wsgi_application', 1),
    ('Python/WSGI/Application', 1),
    ('Python/WSGI/Response', 1),
    ('Python/WSGI/Finalize', 1)
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('get', group='Uri',
    scoped_metrics=_test_wsgi_http_server_get_scoped_metrics)
def test_wsgi_http_server_get():
    response = _test_application.get('/get')
    response.mustcontain('WSGI RESPONSE')

_test_wsgi_http_server_post_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/test_wsgi_http_server:wsgi_application', 1),
    ('Python/WSGI/Application', 1),
    ('Python/WSGI/Response', 1),
    ('Python/WSGI/Finalize', 1)
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('post', group='Uri',
    scoped_metrics=_test_wsgi_http_server_post_scoped_metrics)
def test_wsgi_http_server_post():
    response = _test_application.post('/post', params={'a': 'b'})
    response.mustcontain('WSGI RESPONSE')
