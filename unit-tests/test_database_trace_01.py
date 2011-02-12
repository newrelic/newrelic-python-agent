import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class DatabaseTraceTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_database_trace(self):
        environ = { "REQUEST_URI": "/database_trace" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.1)
            with _newrelic.DatabaseTrace(transaction, "select * from cat"):
                time.sleep(0.1)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = _newrelic.WebTransaction(application, environ)
        try:
            with _newrelic.DatabaseTrace(transaction, "select * from cat"):
                time.sleep(0.1)
        except RuntimeError:
            pass

if __name__ == '__main__':
    unittest.main()
