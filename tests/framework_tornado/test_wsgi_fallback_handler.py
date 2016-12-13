import webtest
import threading

import tornado
import tornado.ioloop

from newrelic.packages import six

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, raise_background_exceptions,
    wait_for_background_threads)

from newrelic.agent import function_wrapper

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

def wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'WSGI RESPONSE'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

server_thread = None
server_ready = threading.Event()

# HTTP listener port will be of form 2mmnn.

http_port = int('2%02d%02d' % tornado.version_info[:2])

@function_wrapper
def setup_application_server(wrapped, instance, args, kwargs):
    global server_thread

    def run():
        import tornado.web
        import tornado.wsgi

        wsgi_container = tornado.wsgi.WSGIContainer(wsgi_application)

        application = tornado.web.Application([
            (r'/get', tornado.web.FallbackHandler, dict(fallback=wsgi_container)),
            (r'/post', tornado.web.FallbackHandler, dict(fallback=wsgi_container)),
        ])

        application.listen(http_port)
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

_test_application = webtest.TestApp('http://localhost:%d' % http_port)

test_wsgi_fallback_handler_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 2),
    ('Function/tornado.web:FallbackHandler.prepare', 1),
    ('Function/test_wsgi_fallback_handler:wsgi_application', 1),
    ('Python/WSGI/Application', 1),
    ('Python/WSGI/Response', 1),
    ('Python/WSGI/Finalize', 1)
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('get', group='Uri',
    scoped_metrics=test_wsgi_fallback_handler_get_scoped_metrics)
@wait_for_background_threads()
def test_wsgi_fallback_handler_get():
    response = _test_application.get('/get')
    response.mustcontain('WSGI RESPONSE')

test_wsgi_fallback_handler_post_scoped_metrics = [
    ('Python/Tornado/Request/Process', 2),
    ('Function/tornado.web:FallbackHandler.prepare', 1),
    ('Function/test_wsgi_fallback_handler:wsgi_application', 1),
    ('Python/WSGI/Application', 1),
    ('Python/WSGI/Response', 1),
    ('Python/WSGI/Finalize', 1)
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('post', group='Uri',
    scoped_metrics=test_wsgi_fallback_handler_post_scoped_metrics)
@wait_for_background_threads()
def test_wsgi_fallback_handler_post():
    response = _test_application.post('/post', params={'a': 'b'})
    response.mustcontain('WSGI RESPONSE')
