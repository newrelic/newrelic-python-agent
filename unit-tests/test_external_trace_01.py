import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class ExternalTraceTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_external_trace(self):
        environ = { "REQUEST_URI": "/external_trace" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.1)
            with _newrelic.ExternalTrace(transaction, "http://localhost/"):
                time.sleep(0.1)
            time.sleep(0.1)

if __name__ == '__main__':
    unittest.main()
