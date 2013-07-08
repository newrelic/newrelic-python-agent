import logging
import unittest
import time
import sys

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.memcache_trace

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

@newrelic.api.memcache_trace.memcache_trace(command="get")
def _test_function_1(command):
    time.sleep(1.0)

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

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
