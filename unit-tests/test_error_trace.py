import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = _newrelic.LOG_VERBOSEDEBUG

settings.error_collector.ignore_errors = ['exceptions.NotImplementedError']

application = _newrelic.application("UnitTests")

@_newrelic.error_trace()
def function_1():
    raise RuntimeError("runtime_error 1")

def function_2():
    raise RuntimeError("runtime_error 2")

@_newrelic.error_trace()
def function_3():
    raise NotImplementedError("runtime_error 3")

class ErrorTraceTransactionTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/error_trace" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                with _newrelic.ErrorTrace(transaction):
                    raise RuntimeError("runtime_error")
            except:
                pass

    def test_implicit_runtime_error_decorator(self):
        environ = { "REQUEST_URI": "/error_trace_decorator" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_1()
            except:
                pass

    def test_implicit_runtime_error_wrap(self):
        environ = { "REQUEST_URI": "/error_trace_wrap" }
        transaction = _newrelic.WebTransaction(application, environ)
        _newrelic.wrap_error_trace(__name__, None, 'function_2')
        with transaction:
            time.sleep(0.5)
            try:
                function_2()
            except:
                pass

    def test_implicit_runtime_error_ignore(self):
        environ = { "REQUEST_URI": "/error_trace_ignore" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_3()
            except:
                pass

if __name__ == '__main__':
    unittest.main()
