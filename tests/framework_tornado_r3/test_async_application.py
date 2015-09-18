import unittest
import pytest
import tornado.testing

import select
import time

from newrelic.agent import wrap_function_wrapper
from newrelic.packages import six

from _test_async_application import (get_tornado_app, HelloRequestHandler,
        SleepRequestHandler, OneCallbackRequestHandler,
        NamedStackContextWrapRequestHandler, MultipleCallbacksRequestHandler)

from testing_support.fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_time_transaction_metrics,
    tornado_validate_errors)

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

    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:HelloRequestHandler.get')
    def test_simple_response(self):
        response = self.fetch_response('/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, HelloRequestHandler.RESPONSE)

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

    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.get',
            scoped_metrics=[
                    ('Function/_test_async_application:OneCallbackRequestHandler.finish_callback',
                     1)])
    def test_one_callback(self):
        response = self.fetch_response('/one-callback')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, OneCallbackRequestHandler.RESPONSE)

    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:NamedStackContextWrapRequestHandler.get',
            scoped_metrics=[
                    ('Function/_test_async_application:NamedStackContextWrapRequestHandler.finish_callback',
                     1)])
    def test_named_wrapped_callback(self):
        response = self.fetch_response('/named-wrap-callback')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                NamedStackContextWrapRequestHandler.RESPONSE)

    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:MultipleCallbacksRequestHandler.get',
            scoped_metrics=[
                ('Function/_test_async_application:MultipleCallbacksRequestHandler.finish_callback',
                 1),
                ('Function/_test_async_application:MultipleCallbacksRequestHandler.counter_callback',
                 2)])
    def test_multiple_callbacks(self):
        response = self.fetch_response('/multiple-callbacks')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                MultipleCallbacksRequestHandler.RESPONSE)

    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:ZeroDivisionError',
            py3='builtins:ZeroDivisionError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncExceptionRequestHandler.get')
    def test_sync_exception(self):
        self.fetch_exception('/sync-exception')

    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:NameError', py3='builtins:NameError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallbackExceptionRequestHandler.get',
            scoped_metrics=[
                ('Function/_test_async_application:CallbackExceptionRequestHandler.counter_callback',
                 5)])
    def test_callback_exception(self):
        self.fetch_exception('/callback-exception')

    @tornado_validate_errors(errors=['tornado.gen:BadYieldError'])
    @tornado_validate_count_transaction_metrics('_test_async_application:CoroutineExceptionRequestHandler.get')
    def test_coroutine_exception(self):
        self.fetch_exception('/coroutine-exception')
