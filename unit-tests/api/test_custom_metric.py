# vim: set fileencoding=utf-8 :

import logging
import unittest
import math

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

application = newrelic.api.application.application_instance("UnitTests")

class CustomMetricTests(unittest.TestCase):

    def setUp(self):
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

    def test_int(self):
        for i in range(100):
            application.record_metric("CustomMetricTests01/Int", i)

    def test_float(self):
        for i in map(math.sqrt, range(100)):
            application.record_metric("CustomMetricTests01/Float", i)

    def test_unicode(self):
        for i in map(math.sqrt, range(100)):
            application.record_metric(u"CustomMetricTests01/√√√√√", i)

    def test_disabled(self):
        application.enabled = False
        application.record_metric("CustomMetricTests01/Disabled", 1)
        application.enabled = True

if __name__ == '__main__':
    unittest.main()
