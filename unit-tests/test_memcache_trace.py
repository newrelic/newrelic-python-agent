import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

#@_newrelic.memcache_trace(command="get")
def _test_function_1(command):
    time.sleep(1.0)
_test_function_1 = _newrelic.memcache_trace(command="get")(_test_function_1)

class MemcacheTraceTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_memcache_trace(self):
        environ = { "REQUEST_URI": "/memcache_trace" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.1)
            with _newrelic.MemcacheTrace(transaction, "get"):
                time.sleep(0.1)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = _newrelic.WebTransaction(application, environ)
        try:
            with _newrelic.MemcacheTrace(transaction, "get"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_memcache_trace_decorator(self):
        environ = { "REQUEST_URI": "/memcache_trace_decorator" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1("set")
            time.sleep(0.1)

    def test_memcache_trace_decorator_error(self):
        environ = { "REQUEST_URI": "/memcache_trace_decorator_error" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            try:
                _test_function_1("set", None)
            except TypeError:
                pass

if __name__ == '__main__':
    unittest.main()
