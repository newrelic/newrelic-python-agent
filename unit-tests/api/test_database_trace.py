import unittest
import time
import sys

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.database_trace

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

application = newrelic.api.application.application("UnitTests")

@newrelic.api.database_trace.database_trace(lambda sql: sql)
def _test_function_1(sql):
    time.sleep(1.0)

class DatabaseTraceTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

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

if __name__ == '__main__':
    unittest.main()
