import unittest

import _newrelic

import math
import time

class CustomMetricTests01(unittest.TestCase):

    def test_int(self):
        application = _newrelic.Application("UnitTests")
        _newrelic.harvest()
        time.sleep(0.1)
        for i in range(100):
            application.custom_metric("CustomMetricTests01/Int", i)
        _newrelic.harvest()

    def test_float(self):
        application = _newrelic.Application("UnitTests")
        _newrelic.harvest()
        time.sleep(0.1)
        for i in map(math.sqrt, range(100)):
            application.custom_metric("CustomMetricTests01/Float", i)
        _newrelic.harvest()

if __name__ == '__main__':
    unittest.main()
