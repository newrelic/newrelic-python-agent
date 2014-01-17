# vim: set fileencoding=utf-8 :

import logging
import sys
import time
import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.error_trace

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

class Error(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

@newrelic.api.error_trace.error_trace()
def function_1():
    raise RuntimeError("runtime_error 1")

def function_2():
    raise Error("runtime_error 2")

@newrelic.api.error_trace.error_trace(ignore_errors=['%s.Error' % __name__])
def function_3():
    raise Error("runtime_error 3")

@newrelic.api.error_trace.error_trace(ignore_errors=['%s:Error' % __name__])
def function_4():
    raise Error("runtime_error 4")

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/error_trace" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                with newrelic.api.error_trace.ErrorTrace(transaction):
                    raise RuntimeError("runtime_error")
            except Exception:
                pass

    def test_implicit_runtime_error_decorator(self):
        environ = { "REQUEST_URI": "/error_trace_decorator" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_1()
            except Exception:
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
            except Exception:
                pass

    def test_implicit_runtime_error_ignore_dot(self):
        environ = { "REQUEST_URI": "/error_trace_ignore_dot" }
        transaction = newrelic.api.web_transaction.WebTransaction(
              application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_3()
            except Exception:
                pass

    def test_implicit_runtime_error_ignore_colon(self):
        environ = { "REQUEST_URI": "/error_trace_ignore_colon" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                function_4()
            except Exception:
                pass

    def test_implicit_runtime_error_unicode(self):
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
            except Exception:
                pass

    def test_implicit_runtime_error_invalid_utf8_byte_string(self):
        environ = { "REQUEST_URI": "/error_trace_invalid_utf8" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.5)
            try:
                with newrelic.api.error_trace.ErrorTrace(transaction):
                    import sys
                    raise RuntimeError(b"runtime_error %s \xe2" %
                                       sys.getdefaultencoding())
            except Exception:
                pass

    # These have 'zzz' and numbers in names to force them to be last
    # and to enforce the order in which they are run.

    def test_zzz_error_limit_1(self):
        environ = { "REQUEST_URI": "/per_transaction_limit" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(2.0)
            for i in range(25):
                try:
                    with newrelic.api.error_trace.ErrorTrace(transaction):
                        raise RuntimeError("runtime_error %d" % i)
                except Exception:
                    pass

    def test_zzz_error_limit_2(self):
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
                    except Exception:
                        pass

if __name__ == '__main__':
    unittest.main()
