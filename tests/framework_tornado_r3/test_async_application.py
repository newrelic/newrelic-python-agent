import unittest
import pytest
import tornado.testing

import select
import time
import threading

from newrelic.agent import wrap_function_wrapper
from newrelic.packages import six

from _test_async_application import (get_tornado_app, HelloRequestHandler,
        SleepRequestHandler, OneCallbackRequestHandler,
        NamedStackContextWrapRequestHandler, MultipleCallbacksRequestHandler,
        FinishExceptionRequestHandler, ReturnExceptionRequestHandler,
        IOLoopDivideRequestHandler,)

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_time_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty)

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

class TornadoTest(tornado.testing.AsyncHTTPTestCase):

    def setUp(self):
        super(TornadoTest, self).setUp()

        # We wrap record_transaction in every test because we want this wrapping
        # to happen after the one in test fixture. Since that's a session scoped
        # fixture that will hapen after the module is loaded but before the
        # tests are invoked. It may be possible to change the scoping of the
        # fixture (module level?) and wrap is on the module level.
        wrap_function_wrapper('newrelic.core.stats_engine',
                'StatsEngine.record_transaction',
                self.stop_after_record_transaction)

        self.waits_expected = 0
        self.waits_counter = 0

    def get_app(self):
        return get_tornado_app()

    # These tests validate the server response and the data written
    # in record_transaction. Before we can validate this, we need to ensure that
    # the response has been returned and record_transaction has been called.
    # That means we can not use the default url fetch method provided by the
    # Tornado test framework but instead create our own fetch methods and the
    # associated wait/stop methods.
    def stop_after_record_transaction(self, wrapped, instance, args, kwargs):
        wrapped(*args, **kwargs)
        self.waits_counter_check()

    def fetch_finished(self, response):
        self.waits_counter_check()

    def waits_counter_check(self):
        self.waits_counter += 1;
        if self.waits_counter == self.waits_expected:
            self.stop()

    def fetch_response(self, path, is_http_error=False):
        # For each request we need to wait for 2 events: the response and a call
        # to record transaction.
        self.waits_expected += 2

        # Make a request to the server.
        future = self.http_client.fetch(self.get_url(path), self.fetch_finished)
        try:
            self.wait(timeout=5.0)
        except:
            self.assertTrue(False, "Timeout occured waiting for response")

        # Retrieve the server response. An exception will be raised
        # if the server did not respond successfully.
        try:
            response = future.result()
        except tornado.httpclient.HTTPError:
            if not is_http_error:
                raise
        else:
            self.assertFalse(is_http_error, "Client did not receive an error "
                    "though one was expected.")
            return response

    def fetch_responses(self, paths):
        # For each request we need to wait for 2 events: the response and a call
        # to record transaction.
        self.waits_expected += 2 * len(paths)
        futures = []
        for path in paths:
            futures.append(self.http_client.fetch(
                    self.get_url(path), self.fetch_finished))
        self.wait(timeout=5.0)
        responses = []
        for future in futures:
            responses.append(future.result())
        return responses

    def fetch_exception(self, path):
        # ExpectLog ensures that the expected server side exception occurs and
        # makes the logging to stdout less noisy.
        with tornado.testing.ExpectLog('tornado.application',
                "Uncaught exception GET %s" % path):
            self.fetch_response(path, is_http_error=True)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:HelloRequestHandler.get')
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
            '_test_async_application:SleepRequestHandler.get')
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
            scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['lambda'])
    def test_coroutine_names_not_lambda(self):
        response = self.fetch_response('/ioloop-divide/10000/10')
        expected = (IOLoopDivideRequestHandler.RESPONSE % (
                10000.0, 10.0, 10000.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:IOLoopDivideRequestHandler.get',
            # PYTHON-1810 means We don't properly instrument the first time we
            # enter a coroutine. Once that is fixed we should start seeing a
            # scoped metric and should capture the scoped metric here.
            # scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['lambda'])
    def test_immediate_coroutine_names_not_lambda(self):
        response = self.fetch_response('/ioloop-divide/10000/10/immediate')
        expected = (IOLoopDivideRequestHandler.RESPONSE % (
                10000.0, 10.0, 10000.0/10.0)).encode('ascii')
        self.assertEqual(response.body, expected)
