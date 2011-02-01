import unittest

import _newrelic

class CustomMetricTests01(unittest.TestCase):

    def test_create(self):
        application = _newrelic.Application("UnitTests")
        for value in range(100):
            application.custom_metric("CustomMetricTests01", value)
        _newrelic.harvest()

if __name__ == '__main__':
    unittest.main()
