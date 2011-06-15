import unittest

import _newrelic

settings = _newrelic.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = _newrelic.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

class HarvestTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_execute(self):
        _newrelic.harvest()

    def test_reason(self):
        _newrelic.harvest("reason")

if __name__ == '__main__':
    unittest.main()
