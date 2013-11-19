import logging
import sys
import time
import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.external_trace

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

@newrelic.api.external_trace.external_trace("unit-tests-1a",
        lambda url: url, lambda url: 'GET')
def _test_function_1a(url):
    time.sleep(1.0)

def _test_function_1b(url):
    time.sleep(1.0)

class TestObject(object):
    @newrelic.api.external_trace.external_trace("unit-tests-2",
                                                lambda self, url: url)
    def _test_function_2(self, url):
        time.sleep(1.0)
    @newrelic.api.external_trace.external_trace("unit-tests-3",
                                                lambda cls, url: url)
    @classmethod
    def _test_function_3(cls, url):
        time.sleep(1.0)
    @newrelic.api.external_trace.external_trace("unit-tests-4",
                                                lambda url: url)
    @staticmethod
    def _test_function_4(url):
        time.sleep(1.0)

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_external_trace(self):
        environ = { "REQUEST_URI": "/external_trace" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            with newrelic.api.external_trace.ExternalTrace(transaction,
                    "unit-tests", "http://a:b@external_trace/test/?c=d"):
                time.sleep(0.1)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = newrelic.api.web_transaction.WebTransaction(
               application, environ)
        try:
            with newrelic.api.external_trace.ExternalTrace(transaction,
                    "unit-tests", "http://a:b@transaction_not_running"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_external_trace_decorator(self):
        environ = { "REQUEST_URI": "/external_trace_decorator" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1a("http://a:b@external_trace_decorator_1/c?d=e")
            o = TestObject()
            o._test_function_2("http://a:b@external_trace_decorator_2/c?d=e")
            o._test_function_3("https://a:b@external_trace_decorator_3/c?d=e")
            o._test_function_4("https://a:b@external_trace_decorator_4/c?d=e")
            time.sleep(0.1)
            _test_function_1a("http://a:b@external_trace_decorator_1:80/c?d=e")
            o = TestObject()
            o._test_function_2("http://a:b@external_trace_decorator_2:80/c?d=e")
            o._test_function_3("https://a:b@external_trace_decorator_3:443/c?d=e")
            o._test_function_4("https://a:b@external_trace_decorator_4:443/c?d=e")
            time.sleep(0.1)

    def test_external_trace_decorator_error(self):
        environ = { "REQUEST_URI": "/external_trace_decorator_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            try:
              _test_function_1a("http://external_trace_decorator_error", None)
            except TypeError:
                pass

    def test_external_trace_wrap(self):
        environ = { "REQUEST_URI": "/external_trace_wrap" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        newrelic.api.external_trace.wrap_external_trace(
                __name__, '_test_function_1b', 'unit-tests-1b',
                "http://external_trace_wrap", 'GET')
        with transaction:
            _test_function_1b("http://external_trace_wrap")

    def test_externa_trace_invalid_urls(self):
        environ = { "REQUEST_URI": "/external_trace_invalid_url" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            _test_function_1a("http://invalid_url:xxx")

if __name__ == '__main__':
    unittest.main()
