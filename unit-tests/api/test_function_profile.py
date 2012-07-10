import logging
import sys
import time
import unittest

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.function_profile

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

filename = '%s.dat' % __file__

@newrelic.api.function_profile.function_profile(filename, 0.0, 1)
def _test_function():
    time.sleep(0.1)

class FunctionTraceTests(unittest.TestCase):

    def setUp(self):
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

    def test_function_profile(self):
        for i in range(20):
            _test_function()

if __name__ == '__main__':
    unittest.main()
