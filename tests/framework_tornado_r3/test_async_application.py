import unittest
import pytest
import tornado.testing

import time

from newrelic.agent import wrap_function_wrapper

from _test_async_application import (get_tornado_app, HelloRequestHandler,
        SleepRequestHandler, OneCallbackRequestHandler,
        NamedStackContextWrapRequestHandler, MultipleCallbacksRequestHandler)

from testing_support.fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_time_transaction_metrics,
    tornado_validate_errors)

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

    def fetch_response(self, path):
        # For each request we need to wait for 2 events: the response and a call
        # to record transaction.
        self.waits_expected += 2
        future = self.http_client.fetch(self.get_url(path), self.fetch_finished)
        try:
            self.wait(timeout=5.0)
        except:
            # TODO(bdirks): Verify this fails.
            self.assertTrue(False, "Timeout occured waiting for response")
        response = future.result()
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
        response = self.fetch('/sleep')
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
        self.assertAlmostEqual(duration, 2.1, delta=0.2)
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
