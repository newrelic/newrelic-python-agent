import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class WebTransactionTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_inactive(self):
        self.assertEqual(_newrelic.transaction(), None)

    def test_web_transaction(self):
        environ = { "REQUEST_URI": "/web_transaction" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
            self.assertFalse(transaction.has_been_named)
            self.assertFalse(transaction.background_task)
            time.sleep(1.0)

    def test_named_web_transaction(self):
        environ = { "REQUEST_URI": "DUMMY" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertFalse(transaction.has_been_named)
            path = "/named_web_transaction"
            transaction.path = path
            self.assertTrue(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
            self.assertEqual(transaction.path, path)
            self.assertTrue(transaction.has_been_named)
            time.sleep(1.0)

    def test_background_web_transaction(self):
        environ = { "REQUEST_URI": "DUMMY" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            path = "background_web_transaction"
            transaction.path = path
            self.assertFalse(transaction.background_task)
            transaction.background_task = True
            self.assertTrue(transaction.background_task)
            transaction.background_task = False
            self.assertFalse(transaction.background_task)
            transaction.background_task = True
            self.assertTrue(transaction.background_task)
            time.sleep(1.0)

    def test_exit_on_delete(self):
        environ = { "REQUEST_URI": "/exit_on_delete" }
        transaction = _newrelic.WebTransaction(application, environ)
        transaction.__enter__()
        time.sleep(1.0)
        del transaction
        self.assertEqual(_newrelic.transaction(), None)

    def test_custom_parameters(self):
        environ = { "REQUEST_URI": "/custom_parameters" }
        transaction = _newrelic.WebTransaction(application, environ)
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
        environ = { "REQUEST_URI": "/explicit_runtime_error" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            for i in range(10):
                try:
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.runtime_error(*sys.exc_info())

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/implicit_runtime_error" }
        transaction = _newrelic.WebTransaction(application, environ)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/application_disabled" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
        application.enabled = True

    def test_environ_enabled_bool(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/environ_enabled_bool",
                    "newrelic.enabled": True }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
        application.enabled = True

    def test_environ_disabled_bool(self):
        environ = { "REQUEST_URI": "/environ_disabled_bool",
                    "newrelic.enabled": False }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)

    def test_environ_enabled_string(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/environ_enabled_string",
                    "newrelic.enabled": "On" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
        application.enabled = True

    def test_environ_disabled_string(self):
        environ = { "REQUEST_URI": "/environ_disabled_string",
                    "newrelic.enabled": "Off" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)

    def test_ignore_web_transaction(self):
        environ = { "REQUEST_URI": "/ignore_web_transaction" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertFalse(transaction.ignore)
            transaction.ignore = True
            self.assertTrue(transaction.ignore)
            transaction.ignore = False
            self.assertFalse(transaction.ignore)
            transaction.ignore = True
            self.assertTrue(transaction.ignore)
            self.assertTrue(transaction.enabled)
            time.sleep(1.0)

if __name__ == '__main__':
    unittest.main()
