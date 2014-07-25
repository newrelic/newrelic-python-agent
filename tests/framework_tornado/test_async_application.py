import pytest

import webtest
import threading

import tornado
import tornado.ioloop

from newrelic.packages import six

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, raise_background_exceptions)

from newrelic.agent import function_wrapper

requires_coroutine = pytest.mark.skipif(tornado.version_info[:2] < (3, 0),
        reason="Tornado only added gen.coroutine in 3.0.")

server_thread = None
server_ready = threading.Event()

@function_wrapper
def setup_application_server(wrapped, instance, args, kwargs):
    global server_thread

    def run():
        from _test_async_application import application
        application.listen(8888)
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

_test_application = webtest.TestApp('http://localhost:8888')

_test_async_application_main_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/_test_async_application:MainHandler.get', 1)]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:MainHandler.get',
        scoped_metrics=_test_async_application_main_get_scoped_metrics)
def test_async_application_main_get():
    response = _test_application.get('/main')
    response.mustcontain('MAIN RESPONSE')

_test_async_application_template_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Template/Render/<string>', 1),
        ('Template/Block/body', 1),
        ('Function/_test_async_application:TemplateHandler.get', 1)]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:TemplateHandler.get',
        scoped_metrics=_test_async_application_template_get_scoped_metrics)
def test_async_application_template_get():
    response = _test_application.get('/template')
    response.mustcontain('TEMPLATE RESPONSE')

_test_async_application_delay_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/_test_async_application:DelayHandler.get', 1),
        ('Function/tornado.platform.kqueue:KQueueIOLoop.add_timeout', 1),
        ('Python/Tornado/Callback/Wait', 1),
        ('Function/_test_async_application:DelayHandler.finish', 1)]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:DelayHandler.get',
        scoped_metrics=_test_async_application_delay_get_scoped_metrics)
def test_async_application_delay_get():
    response = _test_application.get('/delay')
    response.mustcontain('DELAY RESPONSE')

_test_async_application_engine_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        #('Function/_test_async_application:EngineHandler.get', 1),
        ('Function/_test_async_application:get', 1),
        #('Function/_test_async_application:EngineHandler.get (generator)', 2),
        ('Function/_test_async_application:get (generator)', 2),
        ('Function/_test_async_application:EngineHandler.callback', 1),
        #('Python/Tornado/Callback/Wait', 1)]
        ]

if six.PY3:
    _test_async_application_engine_get_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_engine_get_scoped_metrics.extend([
        ('Function/_test_async_application:EngineHandler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
#@validate_transaction_metrics('_test_async_application:EngineHandler.get',
@validate_transaction_metrics('_test_async_application:get',
        scoped_metrics=_test_async_application_engine_get_scoped_metrics)
def test_async_application_engine_get():
    response = _test_application.get('/engine')
    response.mustcontain('DELAY RESPONSE')

_test_async_application_engine_return_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        #('Function/_test_async_application:EngineReturnHandler.get', 1),
        ('Function/_test_async_application:get', 1),
        #('Function/_test_async_application:EngineReturnHandler.get (generator)', 2),
        ('Function/_test_async_application:get (generator)', 2),
        ('Function/_test_async_application:EngineReturnHandler.callback', 1),
        #('Python/Tornado/Callback/Wait', 1)]
        ]

if six.PY3:
    _test_async_application_engine_return_get_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_engine_return_get_scoped_metrics.extend([
        ('Function/_test_async_application:EngineReturnHandler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
#@validate_transaction_metrics('_test_async_application:EngineReturnHandler.get',
@validate_transaction_metrics('_test_async_application:get',
        scoped_metrics=_test_async_application_engine_return_get_scoped_metrics)
def test_async_application_engine_return_get():
    response = _test_application.get('/engine_return')
    response.mustcontain('RETURN RESPONSE')

_test_async_application_engine_error_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        #('Function/_test_async_application:EngineErrorHandler.get', 1),
        ('Function/_test_async_application:get', 1),
        #('Function/_test_async_application:EngineErrorHandler.get (generator)', 2),
        ('Function/_test_async_application:get (generator)', 2),
        ('Function/_test_async_application:EngineErrorHandler.callback', 1),
        #('Python/Tornado/Callback/Wait', 1)]
        ]

if six.PY3:
    _test_async_application_engine_error_get_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_engine_error_get_scoped_metrics.extend([
        ('Function/_test_async_application:EngineErrorHandler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=['exceptions:RuntimeError'])
#@validate_transaction_metrics('_test_async_application:EngineErrorHandler.get',
@validate_transaction_metrics('_test_async_application:get',
        scoped_metrics=_test_async_application_engine_error_get_scoped_metrics)
def test_async_application_engine_error_get():
    response = _test_application.get('/engine_error', status=500)

_test_async_application_coroutine_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        #('Function/_test_async_application:CoroutineHandler.get', 1),
        ('Function/_test_async_application:get', 1),
        #('Function/_test_async_application:CoroutineHandler.get (generator)', 2),
        ('Function/_test_async_application:get (generator)', 2),
        #('Python/Tornado/Callback/Wait', 1)]
        ]

if six.PY3:
    _test_async_application_coroutine_get_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_coroutine_get_scoped_metrics.extend([
        ('Function/_test_async_application:CoroutineHandler.finish', 1)])

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
#@validate_transaction_metrics('_test_async_application:CoroutineHandler.get',
@validate_transaction_metrics('_test_async_application:get',
        scoped_metrics=_test_async_application_coroutine_get_scoped_metrics)
def test_async_application_coroutine_get():
    response = _test_application.get('/coroutine')
    response.mustcontain('DELAY RESPONSE')

_test_async_application_coroutine_return_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        #('Function/_test_async_application:CoroutineHandler.get', 1),
        ('Function/_test_async_application:get', 1),
        #('Function/_test_async_application:CoroutineHandler.get (generator)', 2),
        ('Function/_test_async_application:get (generator)', 2),
        ('Function/_test_async_application:CoroutineHandler.callback', 1),
        #('Python/Tornado/Callback/Wait', 1)]
        ]

if six.PY3:
    _test_async_application_coroutine_return_get_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_coroutine_return_get_scoped_metrics.extend([
        ('Function/_test_async_application:CoroutineReturnHandler.finish', 1)])

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
#@validate_transaction_metrics('_test_async_application:CoroutineReturnHandler.get',
@validate_transaction_metrics('_test_async_application:get',
        scoped_metrics=_test_async_application_coroutine_return_get_scoped_metrics)
def test_async_application_coroutine_return_get():
    response = _test_application.get('/coroutine_return')
    response.mustcontain('RETURN RESPONSE')

_test_async_application_coroutine_error_get_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        #('Function/_test_async_application:CoroutineReturnHandler.get', 1),
        ('Function/_test_async_application:get', 1),
        #('Function/_test_async_application:CoroutineReturnHandler.get (generator)', 2),
        ('Function/_test_async_application:get (generator)', 2),
        ('Function/_test_async_application:CoroutineReturnHandler.callback', 1),
        #('Python/Tornado/Callback/Wait', 1)]
        ]

if six.PY3:
    _test_async_application_coroutine_error_get_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_coroutine_error_get_scoped_metrics.extend([
        ('Function/_test_async_application:CoroutineErrorHandler.finish', 1)])

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=['exceptions:RuntimeError'])
#@validate_transaction_metrics('_test_async_application:CoroutineErrorHandler.get',
@validate_transaction_metrics('_test_async_application:get',
        scoped_metrics=_test_async_application_coroutine_error_get_scoped_metrics)
def test_async_application_coroutine_error_get():
    response = _test_application.get('/coroutine_error', status=500)

if six.PY3:
    _test_async_application_404_name = (
            'tornado.web:RequestHandler.get')
else:
    _test_async_application_404_name = (
            'tornado.web:ErrorHandler.get')

_test_async_application_404_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/%s' % _test_async_application_404_name, 1)]

if six.PY3:
    _test_async_application_404_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_404_scoped_metrics.extend([
        ('Function/tornado.web:ErrorHandler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(_test_async_application_404_name,
        scoped_metrics=_test_async_application_404_scoped_metrics)
def test_async_application_404():
    response = _test_application.get('/missing', status=404)
    response.mustcontain(no=['XXX'])

_test_async_application_raise_404_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/_test_async_application:Raise404Handler.get', 1)]

if six.PY3:
    _test_async_application_raise_404_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_raise_404_scoped_metrics.extend([
        ('Function/_test_async_application:Raise404Handler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:Raise404Handler.get',
        scoped_metrics=_test_async_application_raise_404_scoped_metrics)
def test_async_application_raise_404():
    response = _test_application.get('/raise404', status=404)
    response.mustcontain(no=['XXX'])

_test_async_application_main_post_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/_test_async_application:MainHandler.post', 1),
        ('Function/tornado.httputil:parse_body_arguments', 1),]

if six.PY3:
    _test_async_application_main_post_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_main_post_scoped_metrics.extend([
        ('Function/_test_async_application:MainHandler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:MainHandler.post',
        scoped_metrics=_test_async_application_main_post_scoped_metrics)
def test_async_application_main_post():
    response = _test_application.post('/main', params={'a': 'b'})
    response.mustcontain('MAIN RESPONSE')

if six.PY3:
    _test_async_application_main_put_name = (
            'tornado.web:RequestHandler.put')
else:
    _test_async_application_main_put_name = (
            '_test_async_application:MainHandler.put')

_test_async_application_main_put_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/%s' % _test_async_application_main_put_name, 1),
        ('Function/tornado.httputil:parse_body_arguments', 1)]

if six.PY3:
    _test_async_application_main_put_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.finish', 1)])
else:
    _test_async_application_main_put_scoped_metrics.extend([
        ('Function/_test_async_application:MainHandler.finish', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=['tornado.web:HTTPError'])
@validate_transaction_metrics(_test_async_application_main_put_name,
        scoped_metrics=_test_async_application_main_put_scoped_metrics)
def test_async_application_main_put():
    response = _test_application.put('/main', status=405)
    response.mustcontain(no=['XXX'])

_test_async_application_wsgi_scoped_metrics = [
        ('Python/Tornado/Request/Process', 1),
        ('Function/_test_async_application:wsgi_application', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1)]

if six.PY3:
    _test_async_application_wsgi_scoped_metrics.extend([
        ('Function/tornado.web:RequestHandler.get', 1)])
    pass
else:
    _test_async_application_wsgi_scoped_metrics.extend([
        ('Function/tornado.web:FallbackHandler.get', 1)])

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('wsgi', group='Uri',
        scoped_metrics=_test_async_application_wsgi_scoped_metrics)
def test_async_application_wsgi():
    response = _test_application.get('/wsgi')
    response.mustcontain('WSGI RESPONSE')
