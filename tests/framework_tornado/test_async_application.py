import pytest

import webtest
import threading
import select

import tornado
import tornado.ioloop

from newrelic.packages import six

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, raise_background_exceptions,
    wait_for_background_threads)

from newrelic.agent import function_wrapper, callable_name

requires_coroutine = pytest.mark.skipif(tornado.version_info[:2] < (3, 0),
    reason="Tornado only added gen.coroutine in 3.0.")

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

def py2_ioloop_metric_name(method_name=None):

    # IOLoop class name can vary in Python 2, depending
    # on Tornado version and how IO is done:
    #
    #   kqueue (BSD and Mac OS X)
    #   epoll (Linux)
    #   select (default fallback)

    if tornado.version_info[:2] >= (3, 0):
        ioloop_cls = tornado.ioloop.IOLoop.configured_class()
    else:
        ioloop_cls = tornado.ioloop.IOLoop

    metric_name = 'Function/%s' % callable_name(ioloop_cls)

    if method_name:
        metric_name = '%s.%s' % (metric_name, method_name)

    return metric_name

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
    ('Function/_test_async_application:MainHandler.get', 1)
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:MainHandler.get',
    scoped_metrics=_test_async_application_main_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_main_get():
    response = _test_application.get('/main')
    response.mustcontain('MAIN RESPONSE')

_test_async_application_immediate_prepare_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:ImmediatePrepareHandler.prepare', 1),
    ('Function/_test_async_application:ImmediatePrepareHandler.get', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:ImmediatePrepareHandler.get',
    scoped_metrics=_test_async_application_immediate_prepare_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_immediate_prepare_get():
    response = _test_application.get('/immediate_prepare')
    response.mustcontain('PREPARE RESPONSE')

_test_async_application_engine_immediate_prepare_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineImmediatePrepareHandler.prepare', 1),
    ('Function/_test_async_application:EngineImmediatePrepareHandler.get', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineImmediatePrepareHandler.get',
    scoped_metrics=_test_async_application_engine_immediate_prepare_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_immediate_prepare_get():
    response = _test_application.get('/engine_immediate_prepare')
    response.mustcontain('PREPARE RESPONSE')

_test_async_application_engine_multi_list_prepare_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineMultiListPrepareHandler.prepare', 1),
    ('Function/_test_async_application:EngineMultiListPrepareHandler.get', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineMultiListPrepareHandler.get',
    scoped_metrics=_test_async_application_engine_multi_list_prepare_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_multi_list_prepare_get():
    response = _test_application.get('/engine_multi_list_prepare')
    response.mustcontain('PREPARE RESPONSE')

_test_async_application_engine_multi_yield_prepare_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineMultiYieldPrepareHandler.prepare', 1),
    ('Function/_test_async_application:EngineMultiYieldPrepareHandler.get', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineMultiYieldPrepareHandler.get',
    scoped_metrics=_test_async_application_engine_multi_yield_prepare_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_multi_yield_prepare_get():
    response = _test_application.get('/engine_multi_yield_prepare')
    response.mustcontain('PREPARE RESPONSE')

_test_async_application_engine_cascade_prepare_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineCascadePrepareHandler.prepare', 1),
    ('Function/_test_async_application:EngineCascadePrepareHandler.get', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineCascadePrepareHandler.get',
    scoped_metrics=_test_async_application_engine_cascade_prepare_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_cascade_prepare_get():
    response = _test_application.get('/engine_cascade_prepare')
    response.mustcontain('PREPARE RESPONSE')

_test_async_application_engine_external_prepare_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineExternalPrepareHandler.prepare', 1),
    ('Function/_test_async_application:EngineExternalPrepareHandler.get', 1),
]

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineExternalPrepareHandler.get',
    scoped_metrics=_test_async_application_engine_external_prepare_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_external_prepare_get():
    response = _test_application.get('/engine_external_prepare')
    response.mustcontain('PREPARE RESPONSE')

_test_async_application_template_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Template/Render/<string>', 1),
    ('Template/Block/body', 1),
    ('Function/_test_async_application:TemplateHandler.get', 1),
]

_test_async_application_template_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Template/Render/<string>', 1),
    ('Template/Block/body', 1),
    ('Function/_test_async_application:TemplateHandler.get', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:TemplateHandler.get',
    scoped_metrics=_test_async_application_template_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_template_get():
    response = _test_application.get('/template')
    response.mustcontain('TEMPLATE RESPONSE')

_py2_ioloop_add_timeout_metric_name = py2_ioloop_metric_name('add_timeout')

if tornado.version_info[:2] >= (3, 0):
    _py3_ioloop_add_timeout_metric_name = 'Function/tornado.ioloop:PollIOLoop.add_timeout'
else:
    _py3_ioloop_add_timeout_metric_name = 'Function/tornado.ioloop:IOLoop.add_timeout'

_test_async_application_delay_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:DelayHandler.get', 1),
    (select_python_version(
        py2='Function/_test_async_application:DelayHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    (select_python_version(
        py2=_py2_ioloop_add_timeout_metric_name,
        py3=_py3_ioloop_add_timeout_metric_name), 1),
    ('Python/Tornado/Callback/Wait', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:DelayHandler.get',
    scoped_metrics=_test_async_application_delay_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_delay_get():
    response = _test_application.get('/delay')
    response.mustcontain('DELAY RESPONSE')

_test_async_application_engine_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineHandler.get', 1),
    ('Function/_test_async_application:EngineHandler.get (yield)', 2),
    (select_python_version(
        py2='Function/_test_async_application:EngineHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    ('Function/_test_async_application:EngineHandler.callback', 1),
    #('Python/Tornado/Callback/Wait', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineHandler.get',
    scoped_metrics=_test_async_application_engine_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_get():
    response = _test_application.get('/engine')
    response.mustcontain('DELAY RESPONSE')

_test_async_application_engine_return_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineReturnHandler.get', 1),
    ('Function/_test_async_application:EngineReturnHandler.get (yield)', 2),
    (select_python_version(
        py2='Function/_test_async_application:EngineReturnHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    ('Function/_test_async_application:EngineReturnHandler.callback', 1),
    #('Python/Tornado/Callback/Wait', 1),
]

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:EngineReturnHandler.get',
    scoped_metrics=_test_async_application_engine_return_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_return_get():
    response = _test_application.get('/engine_return')
    response.mustcontain('RETURN RESPONSE')

_test_async_application_engine_error_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:EngineErrorHandler.get', 1),
    ('Function/_test_async_application:EngineErrorHandler.get (yield)', 2),
    (select_python_version(
        py2='Function/_test_async_application:EngineErrorHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    ('Function/_test_async_application:EngineErrorHandler.callback', 1),
    #('Python/Tornado/Callback/Wait', 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[select_python_version(
    py2='exceptions:RuntimeError', py3='builtins:RuntimeError')])
@validate_transaction_metrics('_test_async_application:EngineErrorHandler.get',
    scoped_metrics=_test_async_application_engine_error_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_engine_error_get():
    response = _test_application.get('/engine_error', status=500)

_test_async_application_coroutine_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:CoroutineHandler.get', 1),
    ('Function/_test_async_application:CoroutineHandler.get (yield)', 2),
    (select_python_version(
        py2='Function/_test_async_application:CoroutineHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    ('Function/_test_async_application:CoroutineHandler.callback', 1),
    #('Python/Tornado/Callback/Wait', 1),
]

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:CoroutineHandler.get',
    scoped_metrics=_test_async_application_coroutine_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_coroutine_get():
    response = _test_application.get('/coroutine')
    response.mustcontain('DELAY RESPONSE')

_test_async_application_coroutine_return_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:CoroutineReturnHandler.get', 1),
    ('Function/_test_async_application:CoroutineReturnHandler.get (yield)', 2),
    (select_python_version(
        py2='Function/_test_async_application:CoroutineReturnHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    ('Function/_test_async_application:CoroutineReturnHandler.callback', 1),
    #('Python/Tornado/Callback/Wait', 1),
]

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:CoroutineReturnHandler.get',
    scoped_metrics=_test_async_application_coroutine_return_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_coroutine_return_get():
    response = _test_application.get('/coroutine_return')
    response.mustcontain('RETURN RESPONSE')

_test_async_application_coroutine_error_get_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:CoroutineErrorHandler.get', 1),
    ('Function/_test_async_application:CoroutineErrorHandler.get (yield)', 2),
    (select_python_version(
        py2='Function/_test_async_application:CoroutineErrorHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
    ('Function/_test_async_application:CoroutineErrorHandler.callback', 1),
    #('Python/Tornado/Callback/Wait', 1),
]

@requires_coroutine
@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[select_python_version(
    py2='exceptions:RuntimeError', py3='builtins:RuntimeError')])
@validate_transaction_metrics('_test_async_application:CoroutineErrorHandler.get',
    scoped_metrics=_test_async_application_coroutine_error_get_scoped_metrics)
@wait_for_background_threads()
def test_async_application_coroutine_error_get():
    response = _test_application.get('/coroutine_error', status=500)

_test_async_application_404_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/tornado.web:ErrorHandler.prepare', 1),
    (select_python_version(
        py2='Function/tornado.web:ErrorHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(select_python_version(
    py2='tornado.web:ErrorHandler.get',
    py3='tornado.web:RequestHandler.get'),
    scoped_metrics=_test_async_application_404_scoped_metrics)
@wait_for_background_threads()
def test_async_application_404():
    response = _test_application.get('/missing', status=404)
    response.mustcontain(no=['XXX'])

_test_async_application_raise_404_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:Raise404Handler.get', 1),
    (select_python_version(
        py2='Function/_test_async_application:Raise404Handler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:Raise404Handler.get',
    scoped_metrics=_test_async_application_raise_404_scoped_metrics)
@wait_for_background_threads()
def test_async_application_raise_404():
    response = _test_application.get('/raise404', status=404)
    response.mustcontain(no=['XXX'])

_test_async_application_main_post_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    ('Function/_test_async_application:MainHandler.post', 1),
    ('Function/tornado.httputil:parse_body_arguments', 1),
    (select_python_version(
        py2='Function/_test_async_application:MainHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_async_application:MainHandler.post',
    scoped_metrics=_test_async_application_main_post_scoped_metrics)
@wait_for_background_threads()
def test_async_application_main_post():
    response = _test_application.post('/main', params={'a': 'b'})
    response.mustcontain('MAIN RESPONSE')

_test_async_application_main_put_scoped_metrics = [
    ('Python/Tornado/Request/Process', 1),
    (select_python_version(
        py2='Function/_test_async_application:MainHandler.put',
        py3='Function/tornado.web:RequestHandler.put'), 1),
    ('Function/tornado.httputil:parse_body_arguments', 1),
    (select_python_version(
        py2='Function/_test_async_application:MainHandler.finish',
        py3='Function/tornado.web:RequestHandler.finish'), 1),
]

@setup_application_server
@raise_background_exceptions()
@validate_transaction_errors(errors=['tornado.web:HTTPError'])
@validate_transaction_metrics(select_python_version(
    py2='_test_async_application:MainHandler.put',
    py3='tornado.web:RequestHandler.put'),
    scoped_metrics=_test_async_application_main_put_scoped_metrics)
@wait_for_background_threads()
def test_async_application_main_put():
    response = _test_application.put('/main', status=405)
    response.mustcontain(no=['XXX'])
