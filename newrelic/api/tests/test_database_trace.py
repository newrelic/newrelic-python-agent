import unittest
import time
import sys
import logging

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.database_trace

import newrelic.agent

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance(settings.app_name)

@newrelic.api.database_trace.database_trace(lambda sql: sql)
def _test_function_1(sql):
    time.sleep(1.0)

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_database_trace(self):
        environ = { "REQUEST_URI": "/database_trace" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, "select * from cat"):
                time.sleep(1.0)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        try:
            with newrelic.api.database_trace.DatabaseTrace(
                    transaction, "select * from cat"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_database_trace_decorator(self):
        environ = { "REQUEST_URI": "/database_trace_decorator" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1("select * from cat")
            time.sleep(0.1)

    def test_database_trace_decorator_error(self):
        environ = { "REQUEST_URI": "/database_trace_decorator_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            try:
                _test_function_1("select * from cat", None)
            except TypeError:
                pass

    def test_database_stack_trace_limit(self):
        environ = { "REQUEST_URI": "/database_stack_trace_limit" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            for i in range(settings.agent_limits.slow_sql_stack_trace+10):
                time.sleep(0.1)
                _test_function_1("select * from cat")
                time.sleep(0.1)

if __name__ == '__main__':
    unittest.main()
