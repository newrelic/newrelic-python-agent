import unittest
import math

import _newrelic

settings = _newrelic.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class CustomMetricTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_int(self):
        for i in range(100):
            application.record_metric("CustomMetricTests01/Int", i)

    def test_float(self):
        for i in map(math.sqrt, range(100)):
            application.record_metric("CustomMetricTests01/Float", i)

    def test_disabled(self):
        application.enabled = False
        application.record_metric("CustomMetricTests01/Disabled", 1)
        application.enabled = True

if __name__ == '__main__':
    unittest.main()
