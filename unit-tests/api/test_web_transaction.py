import unittest
import time
import sys

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.web_transaction

settings = newrelic.api.settings.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

application = newrelic.api.application.application("UnitTests")

class WebTransactionTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_inactive(self):
        self.assertEqual(newrelic.api.transaction.transaction(), None)

    def test_web_transaction(self):
        environ = { "REQUEST_URI": "/web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(transaction.path, environ["REQUEST_URI"])
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)
            self.assertFalse(transaction.background_task)
            time.sleep(1.0)

    def test_script_name_web_transaction(self):
        environ = { "SCRIPT_NAME": "/script_name_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path, environ["SCRIPT_NAME"])

    def test_path_info_web_transaction(self):
        environ = { "PATH_INFO": "/path_info_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path, environ["PATH_INFO"])

    def test_script_name_path_info_web_transaction(self):
        environ = { "SCRIPT_NAME": "/script_name_",
                    "PATH_INFO": "path_info_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path, environ["SCRIPT_NAME"] + \
                             environ["PATH_INFO"])

    def test_no_path_web_transaction(self):
        environ = {}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path, "<unknown>")

    def test_named_web_transaction(self):
        environ = { "REQUEST_URI": "DUMMY" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            scope = "Function"
            path = "/named_web_transaction"
            transaction.name_transaction(path, scope)
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)
            self.assertEqual(transaction.path, scope+'/'+path)

    def test_background_web_transaction(self):
        environ = { "REQUEST_URI": "DUMMY" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "background_web_transaction"
            transaction.name_transaction(path)
            self.assertFalse(transaction.background_task)
            transaction.background_task = True
            self.assertTrue(transaction.background_task)
            transaction.background_task = False
            self.assertFalse(transaction.background_task)
            transaction.background_task = True
            self.assertTrue(transaction.background_task)

    def test_environ_background_web_transaction_bool(self):
        environ = { "REQUEST_URI": "DUMMY",
                    "newrelic.background_task": True }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "environ_background_web_transaction_bool"
            transaction.name_transaction(path)
            self.assertTrue(transaction.background_task)

    def test_environ_background_web_transaction_string(self):
        environ = { "REQUEST_URI": "DUMMY",
                    "newrelic.background_task": "On" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "environ_background_web_transaction_string"
            transaction.name_transaction(path)
            self.assertTrue(transaction.background_task)

    def test_exit_on_delete(self):
        environ = { "REQUEST_URI": "/exit_on_delete" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        transaction.__enter__()
        del transaction
        self.assertEqual(newrelic.api.transaction.transaction(), None)

    def test_request_parameters(self):
        environ = { "REQUEST_URI": "/request_parameters",
                    "QUERY_STRING": "a=1&a=2&b=3&c" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            pass

    def test_custom_parameters(self):
        environ = { "REQUEST_URI": "/custom_parameters" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
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

    def test_explicit_runtime_error(self):
        environ = { "REQUEST_URI": "/explicit_runtime_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            for i in range(10):
                try:
                    transaction.custom_parameters["1"] = "1" 
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.notice_error(*sys.exc_info())

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/implicit_runtime_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/application_disabled" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)
        application.enabled = True

    def test_environ_enabled_bool(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/environ_enabled_bool",
                    "newrelic.enabled": True }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)
        application.enabled = True

    def test_environ_disabled_bool(self):
        environ = { "REQUEST_URI": "/environ_disabled_bool",
                    "newrelic.enabled": False }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)

    def test_environ_enabled_string(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/environ_enabled_string",
                    "newrelic.enabled": "On" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)
        application.enabled = True

    def test_environ_disabled_string(self):
        environ = { "REQUEST_URI": "/environ_disabled_string",
                    "newrelic.enabled": "Off" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                    transaction)

    def test_ignore_web_transaction(self):
        environ = { "REQUEST_URI": "/ignore_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.ignore)
            transaction.ignore = True
            self.assertTrue(transaction.ignore)
            transaction.ignore = False
            self.assertFalse(transaction.ignore)
            transaction.ignore = True
            self.assertTrue(transaction.ignore)
            self.assertTrue(transaction.enabled)

    def test_environ_ignore_web_transaction_bool(self):
        environ = { "REQUEST_URI": "/environ_ignore_web_transaction_bool",
                    "newrelic.ignore": True }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.ignore)

    def test_environ_ignore_web_transaction_string(self):
        environ = { "REQUEST_URI": "/environ_ignore_web_transaction_string",
                    "newrelic.ignore": "On" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.ignore)

    def test_queue_start(self):
        now = time.time()
        ts = int((now-0.2) * 1000000)
        environ = { "REQUEST_URI": "/queue_start",
                    "HTTP_X_NEWRELIC_QUEUE_START": "t=%d" % ts }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.8)

if __name__ == '__main__':
    unittest.main()
