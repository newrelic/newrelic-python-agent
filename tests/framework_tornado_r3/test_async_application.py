import functools
import time
import threading
import multiprocessing

from tornado.ioloop import IOLoop
import tornado.stack_context
import tornado.testing

from newrelic.agent import background_task
from newrelic.core.agent import agent_instance
from newrelic.core.stats_engine import StatsEngine
from newrelic.core.thread_utilization import _utilization_trackers
from newrelic.packages import six

from tornado_base_test import TornadoBaseTest

from _test_async_application import (HelloRequestHandler,
        SleepRequestHandler, OneCallbackRequestHandler,
        NamedStackContextWrapRequestHandler, MultipleCallbacksRequestHandler,
        CallLaterRequestHandler, FinishExceptionRequestHandler,
        ReturnExceptionRequestHandler, IOLoopDivideRequestHandler,
        EngineDivideRequestHandler, PrepareOnFinishRequestHandler,
        PrepareOnFinishRequestHandlerSubclass, RunSyncAddRequestHandler,
        SimpleStreamingRequestHandler, DoubleWrapRequestHandler,
        FutureDoubleWrapRequestHandler, RunnerRefCountRequestHandler,
        RunnerRefCountSyncGetRequestHandler, RunnerRefCountErrorRequestHandler,
        TransactionAwareFunctionAferFinalize, IgnoreAddHandlerRequestHandler,
        NativeFuturesCoroutine)

from testing_support.mock_external_http_server import MockExternalHTTPServer

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_time_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty,
    tornado_run_validator)

from remove_utilization_tester import remove_utilization_tester

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
        # If the requests were run synchronously they would take >= 4.0 secs.
        self.assertTrue(duration <= 3.9)
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

    scoped_metrics = [
            ('Function/_test_async_application:IOLoopDivideRequestHandler.get',
            1)]

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

    scoped_metrics = [
            ('Function/_test_async_application:'
             'SimpleStreamingRequestHandler.post', 1),
            ('Function/_test_async_application:'
             'SimpleStreamingRequestHandler.data_received', 3),
    ]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SimpleStreamingRequestHandler.post',
            scoped_metrics=scoped_metrics)
    def test_fixed_length_streaming_request_handler(self):

        def make_streaming_request(server):
            # We don't have precise control over the number of chunks that will
            # be streamed so we set the body size somewhere in greater than 2
            # chunks not too much bigger.
            request_body_size = 600
            conn = six.moves.http_client.HTTPConnection(server)
            conn.putrequest('POST', '/stream')
            conn.putheader('Content-Length', str(request_body_size))
            conn.endheaders()
            conn.send(b'a' * request_body_size)
            resp = conn.getresponse()
            msg = resp.read()
            self.assertEqual(msg, SimpleStreamingRequestHandler.RESPONSE)
            conn.close()
            self.io_loop.add_callback(self.waits_counter_check)

        server = 'localhost:%s' % self.get_http_port()
        self.waits_expected = 2
        t = threading.Thread(target=make_streaming_request, args=(server,))
        t.start()
        self.wait(timeout=5.0)
        t.join(5.0)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SimpleStreamingRequestHandler.post',
            scoped_metrics=scoped_metrics)
    def test_dynamic_length_streaming_request_handler(self):

        def make_streaming_request(server):
            # We don't have precise control over how the chunking will be done
            # by tornado so we sent the chunk size to be small.
            num_chunks = 3
            chunk_byte_size = 5
            chunk_hex = hex(chunk_byte_size)[2:]
            chunk = 'a' * chunk_byte_size
            conn = six.moves.http_client.HTTPConnection(server)
            conn.putrequest('POST', '/stream')
            conn.putheader('Transfer-Encoding', 'chunked')
            conn.endheaders()
            for i in range(0, num_chunks):
                to_send = '%s\r\n%s\r\n' % (chunk_hex, chunk)
                conn.send(to_send.encode('ascii'))
            conn.send('0\r\n'.encode('ascii'))
            resp = conn.getresponse()
            msg = resp.read()
            self.assertEqual(msg, SimpleStreamingRequestHandler.RESPONSE)
            conn.close()
            self.io_loop.add_callback(self.waits_counter_check)

        server = 'localhost:%s' % self.get_http_port()
        self.waits_expected = 2
        t = threading.Thread(target=make_streaming_request, args=(server,))
        t.start()
        self.wait(timeout=5.0)
        t.join(5.0)

    scoped_metrics = [
            ('Function/_test_async_application:'
                    'SimpleStreamingRequestHandler.data_received', 1),
            select_python_version(
                py2=('Function/_test_async_application:'
                     'SimpleStreamingRequestHandler.on_connection_close', 1),
                py3=('Function/tornado.web:'
                     'RequestHandler.on_connection_close', 1))]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SimpleStreamingRequestHandler.post',
            scoped_metrics=scoped_metrics)
    def test_dropped_streaming_request_handler(self):

        def make_streaming_request(server):
            # We don't have precise control over the number of chunks that will
            # be streamed so we set the body size somewhere in greater than 2
            # chunks not too much bigger.
            request_body_size = 600
            conn = six.moves.http_client.HTTPConnection(server)
            conn.putrequest('POST', '/stream')
            conn.putheader('Content-Length', str(request_body_size))
            conn.endheaders()
            conn.send(b'a')
            conn.close()
            self.io_loop.add_callback(self.waits_counter_check)

        server = 'localhost:%s' % self.get_http_port()
        self.waits_expected = 2
        t = threading.Thread(target=make_streaming_request, args=(server,))
        t.start()
        self.wait(timeout=5.0)
        t.join(5.0)

    # The port number 8989 matches the port number in MockExternalHTTPServer
    scoped_metrics = [('Function/_test_async_application:'
            'AsyncFetchRequestHandler.get', 1),
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

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(lambda x: x.last_byte_time > 0.0)
    @tornado_run_validator(lambda x: x.last_byte_time > x.start_time)
    @tornado_run_validator(lambda x: x.last_byte_time < x.end_time)
    def test_last_byte_time_hello_world(self):
        response = self.fetch_response('/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, HelloRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(lambda x: x.last_byte_time > 0.0)
    @tornado_run_validator(lambda x: x.last_byte_time > x.start_time)
    @tornado_run_validator(lambda x: x.last_byte_time < x.end_time)
    @tornado_run_validator(lambda x: x.last_byte_time + 0.00999 < x.end_time)
    def test_last_byte_time_sleep(self):
        response = self.fetch_response('/cancel-timer')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, CallLaterRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(lambda x: x.last_byte_time == 0.0)
    def test_connection_closed_streaming_request_handler(self):

        def close_connection_during_request(server):

            # We don't have precise control over the number of chunks that will
            # be streamed so we set the body size somewhere in greater than 2
            # chunks not too much bigger.

            request_body_size = 600
            conn = six.moves.http_client.HTTPConnection(server)
            conn.putrequest('POST', '/stream')
            conn.putheader('Content-Length', str(request_body_size))
            conn.endheaders()

            # Don't send entire request body before closing connection.

            conn.send(b'aaaaa')
            conn.close()
            self.io_loop.add_callback(self.waits_counter_check)

        server = 'localhost:%s' % self.get_http_port()
        t = threading.Thread(target=close_connection_during_request,
                args=(server,))

        self.waits_expected = 2

        t.start()
        self.wait(timeout=5.0)
        t.join(10.0)

    scoped_metrics = [('Function/_test_async_application:'
            'DoubleWrapRequestHandler.get', 1),
            ('Function/_test_async_application:'
             'DoubleWrapRequestHandler.do_stuff', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:DoubleWrapRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_no_double_wrap(self):
        response = self.fetch_response('/double-wrap')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, DoubleWrapRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'FutureDoubleWrapRequestHandler.get', 1),
            ('Function/_test_async_application:'
             'FutureDoubleWrapRequestHandler.resolve_future', 1),
            ('Function/_test_async_application:'
             'FutureDoubleWrapRequestHandler.do_stuff', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:FutureDoubleWrapRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_no_add_done_double_wrap(self):
        response = self.fetch_response('/done-callback-double-wrap/add_done')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                FutureDoubleWrapRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:FutureDoubleWrapRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_no_add_future_double_wrap(self):
        response = self.fetch_response('/done-callback-double-wrap/add_future')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                FutureDoubleWrapRequestHandler.RESPONSE)

    def check_http_dispatcher_metric(transaction_node):
        """Verify that HttpDispatcher time is using response_time, by
        checking that it's value is different than (and less than)
        transaction duration.

        """
        # I need to pass in a StatsEngine object to time_metrics(), even
        # though it's not used.

        empty_stats = StatsEngine()

        http_dispatcher_metric = next(m for m
                in transaction_node.time_metrics(empty_stats)
                if m.name == 'HttpDispatcher')

        return http_dispatcher_metric.duration < transaction_node.duration

    def check_duration_intrinsic_attribute(transaction_node):
        """Verify that `duration` is using response_time."""

        empty_stats = StatsEngine()

        transaction_event = transaction_node.transaction_event(empty_stats)
        intrinsics, _, _ = transaction_event

        return intrinsics['duration'] < transaction_node.duration

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(lambda x: x.response_time < x.duration)
    @tornado_run_validator(check_http_dispatcher_metric)
    @tornado_run_validator(check_duration_intrinsic_attribute)
    def test_http_dispatcher_uses_response_time_not_duration(self):
        response = self.fetch_response('/call-at')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, CallLaterRequestHandler.RESPONSE)

    def check_total_time_metrics(transaction_node):
        """Verify that the two TotalTime metrics for a transaction have
        the same value as the transaction duration.

        For web transactions, the metrics start with:

            WebTransactionTotalTime/

        For background transactions, the metrics start with:

            OtherTransactionTotalTime/

        """
        # I need to pass in a StatsEngine object to time_metrics(), even
        # though it's not used.

        empty_stats = StatsEngine()

        metrics = [m for m
                in transaction_node.time_metrics(empty_stats)
                if 'TransactionTotalTime' in m.name]
        assert len(metrics) == 2

        return all(metric.duration == transaction_node.duration
                for metric in metrics)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(check_total_time_metrics)
    def test_total_time_metrics_use_duration_web_transaction(self):
        response = self.fetch_response('/call-at')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, CallLaterRequestHandler.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(check_total_time_metrics)
    @background_task()
    def test_total_time_metrics_use_duration_background_task(self):
        time.sleep(0.1)

    scoped_metrics = [('Function/_test_async_application:'
            'RunnerRefCountRequestHandler.get', 1),
            ('Function/_test_async_application:'
             'RunnerRefCountRequestHandler.coro', 1),
            ('Function/_test_async_application:'
             'RunnerRefCountRequestHandler.do_stuff', 1)]

    # The class name is missing from the coroutine metrics in python 2,
    # even though it should be present. See PYTHON-1798.

    coroutine_metrics = [
        select_python_version(
            py2=('Function/_test_async_application:get (coroutine)', 1),
            py3=('Function/_test_async_application:'
                 'RunnerRefCountRequestHandler.get (coroutine)', 1)),
        select_python_version(
            py2=('Function/_test_async_application:coro (coroutine)', 1),
            py3=('Function/_test_async_application:'
                 'RunnerRefCountRequestHandler.coro (coroutine)', 1))]

    scoped_metrics.extend(coroutine_metrics)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:RunnerRefCountRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_runner_ref_count(self):
        response = self.fetch_response('/runner')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, RunnerRefCountRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'RunnerRefCountSyncGetRequestHandler.get', 1),
            ('Function/_test_async_application:'
             'RunnerRefCountSyncGetRequestHandler.coro', 1),
            ('Function/_test_async_application:'
             'RunnerRefCountSyncGetRequestHandler.do_stuff', 1)]

    # The class name is missing from the coroutine metrics in python 2,
    # even though it should be present. See PYTHON-1798.

    coroutine_metrics = [
        select_python_version(
            py2=('Function/_test_async_application:coro (coroutine)', 1),
            py3=('Function/_test_async_application:'
                 'RunnerRefCountSyncGetRequestHandler.coro (coroutine)', 1))]

    scoped_metrics.extend(coroutine_metrics)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:RunnerRefCountSyncGetRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_runner_ref_count_sync_get(self):
        response = self.fetch_response('/runner-sync-get')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                RunnerRefCountSyncGetRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'RunnerRefCountErrorRequestHandler.get', 1),
            ('Function/_test_async_application:'
             'RunnerRefCountErrorRequestHandler.coro', 1)]

    # The class name is missing from the coroutine metrics in python 2,
    # even though it should be present. See PYTHON-1798.

    coroutine_metrics = [
        select_python_version(
            py2=('Function/_test_async_application:get (coroutine)', 1),
            py3=('Function/_test_async_application:'
                 'RunnerRefCountErrorRequestHandler.get (coroutine)', 1)),
        select_python_version(
            py2=('Function/_test_async_application:coro (coroutine)', 1),
            py3=('Function/_test_async_application:'
                 'RunnerRefCountErrorRequestHandler.coro (coroutine)', 1))]

    scoped_metrics.extend(coroutine_metrics)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:ZeroDivisionError',
            py3='builtins:ZeroDivisionError')],
            expect_transaction=True)
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:RunnerRefCountErrorRequestHandler.get',
            scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['do_stuff'])
    def test_runner_ref_count_error(self):
        response = self.fetch_exception('/runner-error')

    # The purpose of this test is to ensure ioloop.handle_callback_exception
    # does not crash when the passed in argument is not a function.
    # This is a departure from our usually end-to-end tests of making a
    # request handler and exercising it because the tornado test machinery
    # will catch the exception itself before our instrumentation of the ioloop
    # has a chance to capture and log the error.
    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors = [],
                             app_exceptions=[select_python_version(
                                     py2='exceptions:Exception',
                                     py3='builtins:Exception')] * 5,
                             expect_transaction=False)
    def test_handle_callback_exception(self):
        # We need to call handle_callback_exception in an exception context or
        # an error occurs when Tornado tries to log the error.
        try:
            raise Exception("We expect this exception to be logged.")
        except:
            io_loop = IOLoop.current()
            io_loop.handle_callback_exception(("foo", "bar"))
            io_loop.handle_callback_exception({})
            io_loop.handle_callback_exception(5)
            io_loop.handle_callback_exception("A string")
            io_loop.handle_callback_exception(object())

    # This tests that we ignore recorded partial functions if the new relic
    # attribute is set. Like the above test, we do not do an end-to-end test
    # but instead add a more traditional unit test because the tornado testing
    # internals will catch the exception before the ioloop exception handler
    # catches it.
    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors = [],
                             app_exceptions=[select_python_version(
                                     py2='__builtin__:NoneType',
                                     py3='builtins:NoneType')],
                             expect_transaction=False)
    def test_handle_callback_exception_already_recorded(self):

        # Create a callback wrapped in a stack context and a partial to mimic
        # the tornado internals.
        def cb(foo, bar):
            pass

        fxn = tornado.stack_context.wrap(cb)
        fxn = functools.partial(fxn, 1)

        # Tests that an exception will be recorded.
        io_loop = IOLoop.current()
        io_loop.handle_callback_exception(fxn)

        # If the _nr_recorded_exception is set we do not record another
        # exception.
        fxn.func._nr_last_object._nr_recorded_exception = True
        io_loop.handle_callback_exception(fxn)


    # For these thread utilization tests, we want to make sure that both the
    # transaction isn't sending up attributes related to thread utilization,
    # and also that the harvest isn't sending up utilization metrics, which are
    # used for "capacity" in APM. We check this by asserting that the machinery
    # that generates these metrics, thread_utilization_data_source & it's
    # 'Thread Utilization' data sampler, have been removed. _utilization_trackers
    # is actually used by transactions, and should agree with the
    # tornado_run_validator check, but we check that it is also clear here,
    # for completeness.

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_run_validator(lambda x:
            'thread.concurrency' not in [i.name for i in x.agent_attributes])
    def test_thread_utilization_disabled_on_transaction(self):
        # Since this test suite imported tornado, we should see that the thread
        # utilization attributes are not on the transaction.

        response = self.fetch_response('/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, HelloRequestHandler.RESPONSE)

    # What we want to test here is code that is executed during agent
    # initialization/registration. Thus we launch the agent in a new process
    # so that we can run the import-initialization-registration process
    # manually and make assertions against it.

    def test_thread_utilization_disabled_immediate(self):
        q = multiprocessing.Queue()
        process = multiprocessing.Process(target=remove_utilization_tester,
                kwargs={'queue': q})
        process.start()
        result = q.get(timeout=15)

        assert result == 'PASS'

    def test_thread_utilization_disabled_scheduled(self):
        q = multiprocessing.Queue()
        process = multiprocessing.Process(target=remove_utilization_tester,
                kwargs={'now': False, 'queue': q})
        process.start()
        result = q.get(timeout=15)

        assert result == 'PASS'

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:TransactionAwareFunctionAferFinalize.get',
            forgone_metric_substrings=['orphan'])
    def test_transaction_aware_function_ran_after_finalize(self):
        self.waits_expected += 1
        TransactionAwareFunctionAferFinalize.set_cleanup(
                self.waits_counter_check)

        response = self.fetch_response('/orphan')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                TransactionAwareFunctionAferFinalize.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'IgnoreAddHandlerRequestHandler.get', 1),
            ('Function/_test_async_application:'
             'IgnoreAddHandlerRequestHandler.send_message', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:IgnoreAddHandlerRequestHandler.get',
            scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['handle_message'])
    def test_add_handler_ignore(self):
        response = self.fetch_response('/add-handler-ignore')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                IgnoreAddHandlerRequestHandler.RESPONSE)

    scoped_metrics = [
        select_python_version(
            py2=('Function/_test_async_application:get (coroutine)', 1),
            py3=('Function/_test_async_application:'
                 'NativeFuturesCoroutine.get (coroutine)', 1)),
            ('Function/_test_async_application:NativeFuturesCoroutine.'
                 'do_thing', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:NativeFuturesCoroutine.get',
            scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['resolve', 'another_method'])
    def test_coroutine_yields_native_future_resolves_outside_transaction(self):
        response = self.fetch_response('/native-future-coroutine/none-context')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                NativeFuturesCoroutine.RESPONSE)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:NativeFuturesCoroutine.get',
            scoped_metrics=[],
            forgone_metric_substrings=['resolve', 'another_method'])
    def test_coroutine_yields_native_future_resolves_in_thread(self):
        response = self.fetch_response('/native-future-coroutine/thread')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                NativeFuturesCoroutine.THREAD_RESPONSE)
