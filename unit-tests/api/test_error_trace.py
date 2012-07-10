# vim: set fileencoding=utf-8 :
  
import logging
import sys
import time
import unittest

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.error_trace

_logger = logging.getLogger('newrelic')

settings = newrelic.api.settings.settings()

settings.host = 'staging-collector.newrelic.com'
settings.license_key = '84325f47e9dec80613e262be4236088a9983d501'

settings.app_name = 'Python Unit Tests'

settings.log_file = '%s.log' % __file__
settings.log_level = logging.DEBUG

settings.transaction_tracer.transaction_threshold = 0
settings.transaction_tracer.stack_trace_threshold = 0

settings.shutdown_timeout = 10.0

settings.debug.log_data_collector_calls = True
settings.debug.log_data_collector_payloads = True

application = newrelic.api.application.application_instance()
application.activate(timeout=10.0)

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
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

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

    def test_per_transaction_limit(self):
        environ = { "REQUEST_URI": "/per_transaction_limit" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(2.0)
            for i in range(25):
                try:
                    with newrelic.api.error_trace.ErrorTrace(transaction):
                        raise RuntimeError("runtime_error %d" % i)
                except:
                    pass

    def test_per_harvest_limit(self):
        environ = { "REQUEST_URI": "/per_harvest_limit" }
        for i in range(5):
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, environ)
            with transaction:
                time.sleep(2.0)
                for i in range(10):
                    try:
                        with newrelic.api.error_trace.ErrorTrace(transaction):
                            raise RuntimeError("runtime_error %d" % i)
                    except:
                        pass

if __name__ == '__main__':
    unittest.main()
