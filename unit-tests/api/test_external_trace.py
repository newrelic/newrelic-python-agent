import unittest
import time
import sys

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.external_trace

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

application = newrelic.api.application.application("UnitTests")

@newrelic.api.external_trace.external_trace("unit-tests-1", lambda url: url)
def _test_function_1(url):
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

class ExternalTraceTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_external_trace(self):
        environ = { "REQUEST_URI": "/external_trace" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            with newrelic.api.external_trace.ExternalTrace(transaction,
                    "unit-tests", "http://a:b@localhost/test/?c=d"):
                time.sleep(0.1)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = newrelic.api.web_transaction.WebTransaction(
               application, environ)
        try:
            with newrelic.api.external_trace.ExternalTrace(transaction,
                    "unit-tests", "http://a:b@localhost/test/?c=d"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_external_trace_decorator(self):
        environ = { "REQUEST_URI": "/external_trace_decorator" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1("http://a:b@localhost/test/?c=d")
            o = TestObject()
            o._test_function_2("http://a:b@localhost/test/?c=d")
            o._test_function_3("http://a:b@localhost/test/?c=d")
            o._test_function_4("http://a:b@localhost/test/?c=d")
            time.sleep(0.1)

    def test_external_trace_decorator_error(self):
        environ = { "REQUEST_URI": "/external_trace_decorator_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            try:
              _test_function_1("http://a:b@localhost/test/?c=d", None)
            except TypeError:
                pass

if __name__ == '__main__':
    unittest.main()
