from __future__ import with_statement

import sys
import time
import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.background_task

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

@newrelic.api.background_task.background_task(settings.app_name,
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

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_no_current_transaction(self):
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_background_task(self):
        name = "background_task"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
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
            group = "Function"
            path = "named_background_task"
            transaction.name_transaction(path, group)
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                             transaction)
            self.assertEqual(transaction.path,
                             'OtherTransaction/'+group+'/'+path)

    def test_exit_on_delete(self):
        name = "exit_on_delete"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        transaction.__enter__()
        del transaction
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_custom_parameters(self):
        name = "custom_parameters"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            transaction.add_custom_parameter("1", "1")
            transaction.add_custom_parameter("2", "2") 
            transaction.add_custom_parameter("3", 3)
            transaction.add_custom_parameter("4", 4.0)
            transaction.add_custom_parameter("5", ("5", 5))
            transaction.add_custom_parameter("6", ["6", 6])
            transaction.add_custom_parameter("7", {"7": 7})
            transaction.add_custom_parameter(8, "8")
            transaction.add_custom_parameter(9.0, "9.0")

    def test_explicit_runtime_error(self):
        name = "explicit_runtime_error"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            for i in range(10):
                try:
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.record_exception(*sys.exc_info())

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
            self.assertEqual(
                    newrelic.api.transaction.current_transaction(), None)
        application.enabled = True

    def test_ignore_background_task(self):
        name = "ignore_background_task"
        transaction = newrelic.api.background_task.BackgroundTask(
                application, name)
        with transaction:
            self.assertFalse(transaction.ignore_transaction)
            transaction.ignore_transaction = True
            self.assertTrue(transaction.ignore_transaction)
            transaction.ignore_transaction = False
            self.assertFalse(transaction.ignore_transaction)
            transaction.ignore_transaction = True
            self.assertTrue(transaction.ignore_transaction)
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
