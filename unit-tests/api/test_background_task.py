import unittest
import time
import sys

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.background_task

settings = newrelic.api.settings.settings()
settings.app_name = "UnitTests"
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

application = newrelic.api.application.application("UnitTests")

@newrelic.api.background_task.background_task("UnitTests",
        name='_test_function_1')
def _test_function_1():
    time.sleep(1.0)

@newrelic.api.background_task.background_task(application)
def _test_function_nn_1():
    time.sleep(0.1)

@newrelic.api.background_task.background_task()
def _test_function_da_1():
    time.sleep(0.1)

@newrelic.api.background_task.background_task(name=lambda x: x)
def _test_function_nl_1(arg):
    time.sleep(0.1)

class BackgroundTaskTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_inactive(self):
        self.assertEqual(newrelic.api.transaction.transaction(), None)

    def test_background_task(self):
        name = "background_task"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                             transaction)
            self.assertTrue(transaction.background_task)
            try:
                transaction.background_task = False
            except AttributeError:
                pass
            time.sleep(1.0)

    def test_named_background_task(self):
        name = "DUMMY"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            scope = "Function"
            path = "named_background_task"
            transaction.name_transaction(path, scope)
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.transaction(),
                             transaction)
            self.assertEqual(transaction.path, scope+'/'+path)

    def test_exit_on_delete(self):
        name = "exit_on_delete"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        transaction.__enter__()
        del transaction
        self.assertEqual(newrelic.api.transaction.transaction(), None)

    def test_custom_parameters(self):
        name = "custom_parameters"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
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
        name = "explicit_runtime_error"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            for i in range(10):
                try:
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.notice_error(*sys.exc_info())

    def test_implicit_runtime_error(self):
        name = "implicit_runtime_error"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        name = "application_disabled"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            self.assertEqual(newrelic.api.transaction.transaction(),
                             transaction)
        application.enabled = True

    def test_ignore_background_task(self):
        name = "ignore_background_task"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            self.assertFalse(transaction.ignore)
            transaction.ignore = True
            self.assertTrue(transaction.ignore)
            transaction.ignore = False
            self.assertFalse(transaction.ignore)
            transaction.ignore = True
            self.assertTrue(transaction.ignore)
            self.assertTrue(transaction.enabled)

    def test_background_task_named_decorator(self):
        _test_function_1()

    def test_background_task_decorator(self):
        _test_function_nn_1()

    def test_background_task_decorator_default(self):
        _test_function_da_1()

    def test_background_task_name_lambda(self):
        _test_function_nl_1('name_lambda')

if __name__ == '__main__':
    unittest.main()
