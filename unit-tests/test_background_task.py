import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.app_name = "UnitTests"
settings.log_file = "%s.log" % __file__
settings.log_level = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

@_newrelic.background_task("UnitTests", name='_test_function_1')
def _test_function_1():
    time.sleep(1.0)

@_newrelic.background_task(application)
def _test_function_nn_1():
    time.sleep(0.1)

@_newrelic.background_task()
def _test_function_da_1():
    time.sleep(0.1)

class BackgroundTaskTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_inactive(self):
        self.assertEqual(_newrelic.transaction(), None)

    def test_background_task(self):
        name = "background_task"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
            self.assertTrue(transaction.background_task)
            try:
                transaction.background_task = False
            except AttributeError:
                pass
            time.sleep(1.0)

    def test_named_background_task(self):
        name = "DUMMY"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            path = "named_background_task"
            transaction.path = path
            self.assertTrue(transaction.enabled)
            self.assertEqual(_newrelic.transaction(), transaction)
            self.assertEqual(transaction.path, path)

    def test_exit_on_delete(self):
        name = "exit_on_delete"
        transaction = _newrelic.BackgroundTask(application, name)
        transaction.__enter__()
        del transaction
        self.assertEqual(_newrelic.transaction(), None)

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

    def test_explicit_runtime_error(self):
        name = "explicit_runtime_error"
        transaction = _newrelic.BackgroundTask(application, name)
        with transaction:
            for i in range(10):
                try:
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.notice_error(*sys.exc_info())
                    import inspect
                    print inspect.getsource(sys.exc_info()[2])

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

    def test_ignore_background_task(self):
        name = "ignore_background_task"
        transaction = _newrelic.BackgroundTask(application, name)
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

if __name__ == '__main__':
    unittest.main()
