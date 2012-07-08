import unittest
import time
import sys

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.memcache_trace

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

application = newrelic.api.application.application_instance("UnitTests")

#@newrelic.api.memcache_trace.memcache_trace(command="get")
def _test_function_1(command):
    time.sleep(1.0)
_test_function_1 = newrelic.api.memcache_trace.memcache_trace(command="get")(
        _test_function_1)

class MemcacheTraceTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_memcache_trace(self):
        environ = { "REQUEST_URI": "/memcache_trace" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            with newrelic.api.memcache_trace.MemcacheTrace(
                    transaction, "get"):
                time.sleep(0.1)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        try:
            with newrelic.api.memcache_trace.MemcacheTrace(
                    transaction, "get"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_memcache_trace_decorator(self):
        environ = { "REQUEST_URI": "/memcache_trace_decorator" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1("set")
            time.sleep(0.1)

    def test_memcache_trace_decorator_error(self):
        environ = { "REQUEST_URI": "/memcache_trace_decorator_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            try:
                _test_function_1("set", None)
            except TypeError:
                pass

if __name__ == '__main__':
    unittest.main()
