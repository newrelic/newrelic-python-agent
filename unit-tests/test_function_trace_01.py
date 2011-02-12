import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class FunctionTraceTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_function_trace(self):
        environ = { "REQUEST_URI": "/function_trace" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.2)
            with _newrelic.FunctionTrace(transaction, "function-1",
                                         "class"):
                time.sleep(0.1)
                with _newrelic.FunctionTrace(transaction, "function-1-1",
                                             "class"):
                    time.sleep(0.1)
                with _newrelic.FunctionTrace(transaction, "function-1-2",
                                             "class"):
                    time.sleep(0.1)
                time.sleep(0.1)
            with _newrelic.FunctionTrace(transaction, "function-2",
                                         "class"):
                time.sleep(0.1)
                with _newrelic.FunctionTrace(transaction, "function-2-1",
                                             "class"):
                    time.sleep(0.1)
                    with _newrelic.FunctionTrace(transaction, "function-2-1-1",
                                                 "class"):
                        time.sleep(0.1)
                    time.sleep(0.1)
                time.sleep(0.1)
            time.sleep(0.2)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = _newrelic.WebTransaction(application, environ)
        try:
            with _newrelic.FunctionTrace(transaction, "function", "class"):
                time.sleep(0.1)
        except RuntimeError:
            pass

if __name__ == '__main__':
    unittest.main()
