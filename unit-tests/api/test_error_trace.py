# vim: set fileencoding=utf-8 :
  
import unittest
import time
import sys

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.error_trace

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

settings.error_collector.ignore_errors = ['exceptions.NotImplementedError']

application = newrelic.api.application.application_instance("UnitTests")

class Error:
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

@newrelic.api.error_trace.error_trace()
def function_1():
    raise RuntimeError("runtime_error 1")

def function_2():
    raise Error("runtime_error 2")

@newrelic.api.error_trace.error_trace()
def function_3():
    raise NotImplementedError("runtime_error 3")

@newrelic.api.error_trace.error_trace(ignore_errors=['__main__.Error'])
def function_4():
    raise Error("runtime_error 4")

class ErrorTraceTransactionTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/error_trace" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                with newrelic.api.error_trace.ErrorTrace(transaction):
                    raise RuntimeError("runtime_error")
            except:
                pass

    def test_implicit_runtime_error_decorator(self):
        environ = { "REQUEST_URI": "/error_trace_decorator" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_1()
            except:
                pass

    def test_implicit_runtime_error_wrap(self):
        environ = { "REQUEST_URI": "/error_trace_wrap" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        newrelic.api.error_trace.wrap_error_trace(__name__, 'function_2')
        with transaction:
            time.sleep(0.5)
            try:
                function_2()
            except:
                pass

    def test_implicit_runtime_error_ignore(self):
        environ = { "REQUEST_URI": "/error_trace_ignore" }
        transaction = newrelic.api.web_transaction.WebTransaction(
              application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_3()
            except:
                pass

    def test_implicit_runtime_error_ignore_api(self):
        environ = { "REQUEST_URI": "/error_trace_ignore_api" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_4()
            except:
                pass

    def test_implicit_runtime_unicode(self):
        environ = { "REQUEST_URI": "/error_trace_unicode" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                with newrelic.api.error_trace.ErrorTrace(transaction):
                    import sys
                    raise RuntimeError(u"runtime_error %s √√√√" %
                                       sys.getdefaultencoding())
            except:
                pass

if __name__ == '__main__':
    unittest.main()
