import unittest
import time
import sys
import random

import _newrelic

settings = _newrelic.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("LoadTests")

class LoadTest02(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_run(self):
        for i in range(2000):
            now = time.time()
            ts = int((now-(random.random()*0.04)) * 1000000)
            environ = { "REQUEST_URI": "/load_test_02",
                        "HTTP_X_NEWRELIC_QUEUE_START": "t=%d" % ts }
            transaction = _newrelic.WebTransaction(application, environ)
            with transaction:
                sys.stderr.write(".")
                time.sleep(random.random()*0.16)
        sys.stderr.write("\n")

if __name__ == '__main__':
    unittest.main()
