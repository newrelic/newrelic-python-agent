import unittest
import time
import sys
import logging

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.database_trace

import newrelic.agent

_logger = logging.getLogger('newrelic')

settings = newrelic.api.settings.settings()

settings.host = 'staging-collector.newrelic.com'
settings.port = 80
settings.license_key = '84325f47e9dec80613e262be4236088a9983d501'

settings.app_name = 'Python Agent Test'

settings.log_file = '%s.log' % __file__
settings.log_level = logging.DEBUG

settings.transaction_tracer.transaction_threshold = 0

# Initialise higher level instrumentation layers. Not
# that they will be used in this test for now.

newrelic.agent.initialize()

# Want to force agent initialisation and connection so
# we know that data will actually get through to core
# and not lost because application not activated. We
# really need a way of saying to the agent that want to
# wait, either indefinitely or for a set period, when
# activating the application. Will make this easier.

import newrelic.core.agent

agent = newrelic.core.agent.agent()

name = settings.app_name
application_settings = agent.application_settings(name)

agent.activate_application(name, timeout=10.0)

application = newrelic.api.application.application(settings.app_name)

@newrelic.api.database_trace.database_trace(lambda sql: sql)
def _test_function_1(sql):
    time.sleep(1.0)

class DatabaseTraceTests(unittest.TestCase):

    def setUp(self):
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

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

    def test_database_trace_decorator(self):
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
