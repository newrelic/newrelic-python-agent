# vim: set fileencoding=utf-8 :
  
import unittest
import math

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

application = newrelic.api.application.application_instance("UnitTests")

class CustomMetricTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

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
