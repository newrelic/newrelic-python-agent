import unittest

import _newrelic

settings = _newrelic.Settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

class HarvestTests01(unittest.TestCase):

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
