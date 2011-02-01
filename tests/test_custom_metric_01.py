import unittest
import math

import _newrelic

settings = _newrelic.Settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

class CustomMetricTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_int(self):
        for i in range(100):
            application.custom_metric("CustomMetricTests01/Int", i)

    def test_float(self):
        for i in map(math.sqrt, range(100)):
            application.custom_metric("CustomMetricTests01/Float", i)

    def test_disabled(self):
        application.enabled = False
        application.custom_metric("CustomMetricTests01/Disabled", 1)
        application.enabled = True

if __name__ == '__main__':
    application = _newrelic.Application("UnitTests")
    unittest.main()
