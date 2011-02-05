import unittest
import time
import sys
import random

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("LoadTests")

class LoadTest02(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_run(self):
        environ = { "REQUEST_URI": "/load_test_02" }
        for i in range(1000):
            transaction = _newrelic.WebTransaction(application, environ)
            with transaction:
                sys.stderr.write(".")
                time.sleep(random.random()*0.1)
        sys.stderr.write("\n")

if __name__ == '__main__':
    unittest.main()
