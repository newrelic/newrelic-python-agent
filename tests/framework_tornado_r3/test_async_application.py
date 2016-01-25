import time
import threading

import tornado.testing

from newrelic.packages import six

from tornado_base_test import TornadoBaseTest

from _test_async_application import (HelloRequestHandler,
        SleepRequestHandler, OneCallbackRequestHandler,
        NamedStackContextWrapRequestHandler, MultipleCallbacksRequestHandler,
        FinishExceptionRequestHandler, ReturnExceptionRequestHandler,
        IOLoopDivideRequestHandler, EngineDivideRequestHandler,
        PrepareOnFinishRequestHandler, PrepareOnFinishRequestHandlerSubclass,
        RunSyncAddRequestHandler, )

from testing_support.mock_external_http_server import MockExternalHTTPServer

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_time_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty)

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

class TornadoTest(TornadoBaseTest):

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:HelloRequestHandler.get',
            forgone_metric_substrings=['prepare', 'on_finish'])
    def test_simple_response(self):
        response = self.fetch_response('/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, HelloRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SleepRequestHandler.get')
    @tornado_validate_time_transaction_metrics(
            '_test_with_unittest:SleepRequestHandler.get',
            custom_metrics = [(
                    'WebTransaction/Function/_test_async_application:SleepRequestHandler.get',
                    (2.0, 2.3))])
    def test_sleep_response(self):
        response = self.fetch_response('/sleep')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, SleepRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SleepRequestHandler.get',
            transaction_count=2)
    @tornado_validate_time_transaction_metrics(
            '_test_with_unittest:SleepRequestHandler.get',
            custom_metrics = [(
                    'WebTransaction/Function/_test_async_application:SleepRequestHandler.get',
                    (2.0, 2.3))])
    def test_sleep_two_clients(self):
        start_time = time.time()
        responses = self.fetch_responses(['/sleep', '/sleep'])
        duration = time.time() - start_time
        # We don't use assertAlmostEqual since delta isn't supported in 2.6.
        # Also assert(Greater|Less)Than is only in > 2.6.
        self.assertTrue(duration >= 2.0)
        self.assertTrue(duration <= 2.3)
        self.assertEqual(responses[0].code, 200)
        self.assertEqual(responses[0].body, SleepRequestHandler.RESPONSE)
        self.assertEqual(responses[1].code, 200)
        self.assertEqual(responses[1].body, SleepRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_one_callback(self):
        response = self.fetch_response('/one-callback')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.post', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.post',
            scoped_metrics=scoped_metrics)
    def test_post_method_one_callback(self):
        response = self.fetch_response('/one-callback', method="POST", body="test")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.head', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.head',
            scoped_metrics=scoped_metrics)
    def test_head_method_one_callback(self):
        response = self.fetch_response('/one-callback', method="HEAD")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.delete', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.delete',
            scoped_metrics=scoped_metrics)
    def test_delete_method_one_callback(self):
        response = self.fetch_response('/one-callback', method="DELETE")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.patch', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.patch',
            scoped_metrics=scoped_metrics)
    def test_patch_method_one_callback(self):
        response = self.fetch_response('/one-callback', method="PATCH", body="test")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.put', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.put',
            scoped_metrics=scoped_metrics)
    def test_put_method_one_callback(self):
        response = self.fetch_response('/one-callback', method="PUT", body="test")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.options', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.options',
            scoped_metrics=scoped_metrics)
    def test_options_method_one_callback(self):
        response = self.fetch_response('/one-callback', method="OPTIONS")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'NamedStackContextWrapRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'NamedStackContextWrapRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:NamedStackContextWrapRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_named_wrapped_callback(self):
        response = self.fetch_response('/named-wrap-callback')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                NamedStackContextWrapRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'MultipleCallbacksRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'MultipleCallbacksRequestHandler.finish_callback', 1),
            ('Function/_test_async_application:'
             'MultipleCallbacksRequestHandler.counter_callback', 2)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:MultipleCallbacksRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_multiple_callbacks(self):
        response = self.fetch_response('/multiple-callbacks')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                MultipleCallbacksRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:ZeroDivisionError',
            py3='builtins:ZeroDivisionError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncExceptionRequestHandler.get')
    def test_sync_exception(self):
        self.fetch_exception('/sync-exception')

    scoped_metrics = [('Function/_test_async_application:'
            'CallbackExceptionRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'CallbackExceptionRequestHandler.counter_callback', 5)]

    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:NameError', py3='builtins:NameError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallbackExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_callback_exception(self):
        self.fetch_exception('/callback-exception')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=['tornado.gen:BadYieldError'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineExceptionRequestHandler.get')
    def test_coroutine_exception(self):
        self.fetch_exception('/coroutine-exception')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:FinishExceptionRequestHandler.get')
    def test_finish_exception(self):
        response = self.fetch_response('/finish-exception')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, FinishExceptionRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:ReturnExceptionRequestHandler.get')
    def test_return_exception(self):
        response = self.fetch_response('/return-exception')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, ReturnExceptionRequestHandler.RESPONSE)


    # The following 3 functions are helper functions used to test exceptions
    # occuring outside of a transaction.
    def after_divide(self):
        self.stop()

    def divide_by_zero(self):
        quotient = 0
        try:
            quotient = 5/0
        finally:
            self.io_loop.add_callback(self.after_divide)
        return quotient

    def schedule_divide_by_zero(self):
        self.io_loop.add_callback(self.divide_by_zero)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[], expect_transaction=False,
            app_exceptions=[select_python_version(
                    py2='exceptions:ZeroDivisionError',
                    py3='builtins:ZeroDivisionError')])
    def test_stack_context_no_transaction_exception(self):
        # This tests that we record exceptions when they are not in a
        # transaction, but they do occur within a stack context. That is they
        # are scheduled asynchronously in a way where one wants to keep track of
        # the stack context, such as via a context manager. Just as a note,
        # it is possible for code written by an application developer to occur
        # within an ExceptionStackContext implicitly, request handlers do this
        # for example.

        # The lambda here is an exception handler which swallows the exception.
        with tornado.stack_context.ExceptionStackContext(
                lambda type, value, traceback: True):
            self.schedule_divide_by_zero()
        self.wait(timeout=5.0)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[], expect_transaction=False,
            app_exceptions=[select_python_version(
                    py2='exceptions:ZeroDivisionError',
                    py3='builtins:ZeroDivisionError')])
    def test_threaded_no_transaction_exception(self):
        # This tests that we record exceptions when an error occurs outside a
        # transaction and outside a stack context. This can be done when a job
        # is scheduled from another thread or is initiated outside of an
        # ExceptionStackContext context manager. By default, tests are run
        # inside an ExceptionStackContext so we spawn a new thread for this
        # test.
        t = threading.Thread(target=self.schedule_divide_by_zero)
        t.start()
        t.join(5.0)
        self.wait(timeout=5.0)

    # The class name is missing from this metric in python 2
    # though it should be present. See PYTHON-1798.
    scoped_metrics = [select_python_version(
            py2=('Function/_test_async_application:get (coroutine)', 1),
            py3=('Function/_test_async_application:IOLoopDivideRequestHandler.'
                 'get (coroutine)', 1))]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:IOLoopDivideRequestHandler.get',
            scoped_metrics=scoped_metrics,)
            # forgone_metric_substrings=['lambda']) # may add after PYTHON-1847
    def test_coroutine_names_not_lambda(self):
        response = self.fetch_response('/ioloop-divide/10000/10')
        expected = (IOLoopDivideRequestHandler.RESPONSE % (
                10000.0, 10.0, 10000.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)

    # We have 2 calls to get. One is from the wrapped request handler and one
    # is from it being a coroutine.
    scoped_metrics = [
            ('Function/_test_async_application:IOLoopDivideRequestHandler.get',
            2)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:IOLoopDivideRequestHandler.get',
            scoped_metrics=scoped_metrics,)
            # forgone_metric_substrings=['lambda']) # may add after PYTHON-1847
    def test_immediate_coroutine_names_not_lambda(self):
        response = self.fetch_response('/ioloop-divide/10000/10/immediate')
        expected = (IOLoopDivideRequestHandler.RESPONSE % (
                10000.0, 10.0, 10000.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)

    # The following 2 tests are the "engine" version of the coroutine tests
    # above.

    # The class name is missing from this metric in python 2
    # though it should be present. See PYTHON-1798.
    scoped_metrics = [select_python_version(
            py2=('Function/_test_async_application:get (coroutine)', 1),
            py3=('Function/_test_async_application:EngineDivideRequestHandler.'
                 'get (coroutine)', 1))]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:EngineDivideRequestHandler.get',
            scoped_metrics=scoped_metrics,)
            # forgone_metric_substrings=['lambda']) # may add after PYTHON-1847
    def test_engine_names_not_lambda(self):
        response = self.fetch_response('/engine-divide/10000/10')
        expected = (EngineDivideRequestHandler.RESPONSE % (
                10000.0, 10.0, 10000.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)

    # There is an issue with callable name. With the coroutine wrapper, we
    # preserve the name of the method and get the class name in the method name
    # path. However, with the gen.engine wrapper, we get the method name without
    # the classname. We get the full name from wrapping the GET request handler.
    scoped_metrics = select_python_version(
            py2=[('Function/_test_async_application:'
                'EngineDivideRequestHandler.get', 1),
                ('Function/_test_async_application:get', 1)],
            py3=[('Function/_test_async_application:EngineDivideRequestHandler.'
                  'get', 2)])

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:EngineDivideRequestHandler.get',
            scoped_metrics=scoped_metrics,)
            # forgone_metric_substrings=['lambda']) # may add after PYTHON-1847
    def test_immediate_engine_names_not_lambda(self):
        response = self.fetch_response('/engine-divide/10000/10/immediate')
        expected = (EngineDivideRequestHandler.RESPONSE % (
                10000.0, 10.0, 10000.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)

    scoped_metrics = select_python_version(
            py2=[('Function/_test_async_application:'
                'NestedCoroutineDivideRequestHandler.do_divide', 1),
                ('Function/_test_async_application:do_divide (coroutine)', 1)],
            py3=[('Function/_test_async_application:'
                'NestedCoroutineDivideRequestHandler.do_divide', 1),
                ('Function/_test_async_application:NestedCoroutineDivide'
                'RequestHandler.do_divide (coroutine)', 1)])

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
        '_test_async_application:NestedCoroutineDivideRequestHandler.get',
        scoped_metrics=scoped_metrics,)
        # forgone_metric_substrings=['lambda']) # may add after PYTHON-1847
    def test_coroutine_first_time(self):
        response = self.fetch_response('/nested-divide/100/10/')
        expected = (EngineDivideRequestHandler.RESPONSE % (
                100.0, 10.0, 100.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)

    scoped_metrics = [('Function/_test_async_application:'
            'PrepareOnFinishRequestHandler.prepare', 1),
            ('Function/_test_async_application:'
            'PrepareOnFinishRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'PrepareOnFinishRequestHandler.on_finish', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:PrepareOnFinishRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_prepare_on_finish_instrumented(self):
        response = self.fetch_response('/bookend')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, PrepareOnFinishRequestHandler.RESPONSE)

    scoped_metrics = [
            select_python_version(
                    py2=('Function/_test_async_application:'
                         'PrepareOnFinishRequestHandlerSubclass.prepare', 1),
                    py3=('Function/_test_async_application:'
                         'PrepareOnFinishRequestHandler.prepare', 1)),
            ('Function/_test_async_application:'
                    'PrepareOnFinishRequestHandlerSubclass.get', 1),
            select_python_version(
                    py2=('Function/_test_async_application:'
                         'PrepareOnFinishRequestHandlerSubclass.on_finish', 1),
                    py3=('Function/_test_async_application:'
                         'PrepareOnFinishRequestHandler.on_finish', 1)),
    ]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:PrepareOnFinishRequestHandlerSubclass.get',
            scoped_metrics=scoped_metrics)
    def test_prepare_on_finish_subclass_instrumented(self):
        response = self.fetch_response('/bookend-subclass')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
            PrepareOnFinishRequestHandlerSubclass.RESPONSE)

    # The port number 8989 matches the port number in MockExternalHTTPServer
    scoped_metrics = [('Function/_test_async_application:'
            'AsyncFetchRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'AsyncFetchRequestHandler.process_response', 1),
            ('Function/_test_async_application:AsyncFetchRequestHandler.'
             'process_response [http://localhost:8989]', 1),
            ('External/localhost:8989/tornado.httpclient/', 1)
    ]

    rollup_metrics = [('External/allWeb', 1), ('External/all', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:AsyncFetchRequestHandler.get',
            scoped_metrics=scoped_metrics,
            rollup_metrics=rollup_metrics)
    def test_async_httpclient_raw_url_fetch(self):
        external = MockExternalHTTPServer()
        external.start()
        response = self.fetch_response('/async-fetch/rawurl/%s' % external.port)
        external.stop()

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, external.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:AsyncFetchRequestHandler.get',
            scoped_metrics=scoped_metrics,
            rollup_metrics=rollup_metrics)
    def test_async_httpclient_request_object_fetch(self):
        external = MockExternalHTTPServer()
        external.start()
        response = self.fetch_response(
                '/async-fetch/requestobj/%s' % external.port)
        external.stop()

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, external.RESPONSE)

    # The port number 8989 matches the port number in MockExternalHTTPServer
    scoped_metrics = [('Function/_test_async_application:'
            'SyncFetchRequestHandler.get', 1),
            ('External/localhost:8989/tornado.httpclient/', 1)
    ]

    rollup_metrics = [('External/allWeb', 1), ('External/all', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncFetchRequestHandler.get',
            scoped_metrics=scoped_metrics,
            rollup_metrics=rollup_metrics)
    def test_sync_httpclient_raw_url_fetch(self):
        external = MockExternalHTTPServer()
        external.start()
        response = self.fetch_response('/sync-fetch/rawurl/%s' % external.port)
        external.stop()

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, external.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncFetchRequestHandler.get',
            scoped_metrics=scoped_metrics,
            rollup_metrics=rollup_metrics)
    def test_sync_httpclient_request_object_fetch(self):
        external = MockExternalHTTPServer()
        external.start()
        response = self.fetch_response(
                '/sync-fetch/requestobj/%s' % external.port)
        external.stop()

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, external.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:RunSyncAddRequestHandler.get')
    def test_run_sync_response(self):
        a = 3
        b = 4
        response = self.fetch_response('/run-sync-add/%s/%s' % (a,b))
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, RunSyncAddRequestHandler.RESPONSE(a+b))
