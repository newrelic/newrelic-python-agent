import logging
import unittest

import newrelic.api.settings
import newrelic.api.application

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

class ApplicationTests(unittest.TestCase):

    def setUp(self):
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

    def test_create(self):
        application = newrelic.api.application.application_instance(
                "UnitTests")
        self.assertEqual(application.name, "UnitTests")

    def test_enabled(self):
        application = newrelic.api.application.application_instance(
                "UnitTests")
        self.assertTrue(application.enabled)
        application.enabled = False
        self.assertFalse(application.enabled)
        application.enabled = True
        self.assertTrue(application.enabled)

    def test_singleton(self):
        application1 = newrelic.api.application.application_instance(
                "UnitTests")
        application2 = newrelic.api.application.application_instance(
                "UnitTests")
        self.assertEqual(id(application1), id(application2))

if __name__ == '__main__':
    unittest.main()
