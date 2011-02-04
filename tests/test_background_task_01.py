import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class BackgroundTaskTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_inactive(self):
        self.assertEqual(_newrelic.transaction(), None)

    def test_transaction(self):
        name = "test_transaction"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            self.assertEqual(_newrelic.transaction(), transaction)
            time.sleep(1.0)

    def test_custom_parameters(self):
        name = "custom_parameters"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            transaction.custom_parameters["1"] = "1" 
            transaction.custom_parameters["2"] = "2" 
            transaction.custom_parameters["3"] = 3
            transaction.custom_parameters["4"] = 4.0
            transaction.custom_parameters["5"] = ("5", 5)
            transaction.custom_parameters["6"] = ["6", 6]
            transaction.custom_parameters["7"] = {"7": 7}
            transaction.custom_parameters[8] = "8"
            transaction.custom_parameters[9.0] = "9.0"
            time.sleep(1.0)

    def test_explicit_runtime_error(self):
        name = "explicit_runtime_error"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            for i in range(10):
                try:
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.runtime_error(*sys.exc_info())

    def test_implicit_runtime_error(self):
        name = "implicit_runtime_error"
        transaction = _newrelic.BackgroundTask(application, name)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        name = "application_disabled"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            self.assertEqual(_newrelic.transaction(), transaction)
        application.enabled = True

    def test_exit_on_delete(self):
        name = "exit_on_delete"
        transaction = _newrelic.BackgroundTask(application, name)
        transaction.__enter__()
        time.sleep(1.0)
        del transaction
        self.assertEqual(_newrelic.transaction(), None)

if __name__ == '__main__':
    unittest.main()
