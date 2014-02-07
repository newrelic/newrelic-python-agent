import threading
import time

from gevent import Timeout, sleep

def request_timeout_application(environ, start_response):
    with Timeout(2.0):
        sleep(10.0)

    status = '200 OK'

    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)

    try:
        yield 'WSGI RESPONSE'
    finally:
        pass

def request_timeout_response(environ, start_response):
    status = '200 OK'

    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)

    yield 'WSGI'

    with Timeout(2.0):
        sleep(10.0)

    yield ' '
    yield 'RESPONSE'

def request_timeout_finalize(environ, start_response):
    status = '200 OK'

    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)

    try:
        yield 'WSGI RESPONSE'

    finally:
        with Timeout(2.0):
            sleep(10.0)

def raise_exception_application(environ, start_response):
    raise RuntimeError('raise_exception_application')

    status = '200 OK'
    output = b'WSGI RESPONSE'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

def raise_exception_response(environ, start_response):
    status = '200 OK'

    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)

    yield 'WSGI'

    raise RuntimeError('raise_exception_response')

    yield ' '
    yield 'RESPONSE'

def raise_exception_finalize(environ, start_response):
    status = '200 OK'

    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)

    try:
        yield 'WSGI RESPONSE'

    finally:
        raise RuntimeError('raise_exception_finalize')

def application_index(environ, start_response):
    status = '200 OK'

    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)

    time.sleep(2.0)

    try:
        yield 'WSGI RESPONSE'
    finally:
        pass

def sample_application(environ, start_response):
    path_info = environ.get('PATH_INFO')

    if path_info.startswith('/request-timeout-application'):
        return request_timeout_application(environ, start_response)
    elif path_info.startswith('/request-timeout-response'):
        return request_timeout_response(environ, start_response)
    elif path_info.startswith('/request-timeout-finalize'):
        return request_timeout_finalize(environ, start_response)
    elif path_info.startswith('/raise-exception-application'):
        return raise_exception_application(environ, start_response)
    elif path_info.startswith('/raise-exception-response'):
        return raise_exception_response(environ, start_response)
    elif path_info.startswith('/raise-exception-finalize'):
        return raise_exception_finalize(environ, start_response)

    return application_index(environ, start_response)

def setup_application():
    def run_wsgi():
        from gevent.wsgi import WSGIServer
        WSGIServer(('', 8001), sample_application).serve_forever()

    wsgi_thread = threading.Thread(target=run_wsgi)
    wsgi_thread.daemon = True
    wsgi_thread.start()

    def run_pywsgi():
        from gevent.pywsgi import WSGIServer
        WSGIServer(('', 8002), sample_application).serve_forever()

    pywsgi_thread = threading.Thread(target=run_pywsgi)
    pywsgi_thread.daemon = True
    pywsgi_thread.start()

    time.sleep(1.0)
