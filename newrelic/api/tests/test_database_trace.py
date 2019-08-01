import unittest
import time

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction

from newrelic.api.database_trace import database_trace, DatabaseTrace

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance(settings.app_name)


@database_trace(lambda sql: sql)
def _test_function_1(sql):
    time.sleep(1.0)


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_database_trace(self):
        environ = {"REQUEST_URI": "/database_trace"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            with newrelic.api.database_trace.DatabaseTrace(
                    "select * from cat"):
                time.sleep(1.0)
            time.sleep(0.1)

    def test_transaction_not_running(self):
        try:
            with newrelic.api.database_trace.DatabaseTrace(
                    "select * from cat"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_database_trace_decorator(self):
        environ = {"REQUEST_URI": "/database_trace_decorator"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1("select * from cat")
            time.sleep(0.1)

    def test_database_trace_decorator_error(self):
        environ = {"REQUEST_URI": "/database_trace_decorator_error"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        with transaction:
            try:
                _test_function_1("select * from cat", None)
            except TypeError:
                pass

    def test_database_trace_saves_host_wo_database_name_reporting(self):
        environ = {"REQUEST_URI": "/database_stack_trace_limit"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)

        ds_settings = transaction.settings.datastore_tracer
        original_instance_reporting = ds_settings.instance_reporting.enabled
        original_database_name_reporting = \
                ds_settings.database_name_reporting.enabled

        ds_settings.instance_reporting.enabled = True
        ds_settings.database_name_reporting.enabled = False

        try:
            with transaction:
                with DatabaseTrace("select * from cat", host='a',
                        port_path_or_id='b', database_name='c',
                        connect_params=None) as trace:

                    trace.finalize_data(transaction)
                    assert trace.host == 'a'
                    assert trace.port_path_or_id == 'b'
                    assert trace.database_name is None

        finally:
            ds_settings.instance_reporting.enabled = \
                original_instance_reporting
            ds_settings.database_name_reporting.enabled = \
                    original_database_name_reporting

    def test_database_trace_saves_database_name_wo_instance_reporting(self):
        environ = {"REQUEST_URI": "/database_stack_trace_limit"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)

        ds_settings = transaction.settings.datastore_tracer
        original_instance_reporting = ds_settings.instance_reporting.enabled
        original_database_name_reporting = \
                ds_settings.database_name_reporting.enabled

        ds_settings.instance_reporting.enabled = False
        ds_settings.database_name_reporting.enabled = True

        try:
            with transaction:
                with DatabaseTrace("select * from cat", host='a',
                        port_path_or_id='b', database_name='c',
                        connect_params=None) as trace:

                    trace.finalize_data(transaction)
                    assert trace.host is None
                    assert trace.port_path_or_id is None
                    assert trace.database_name == 'c'

        finally:
            ds_settings.instance_reporting.enabled = \
                original_instance_reporting
            ds_settings.database_name_reporting.enabled = \
                    original_database_name_reporting


if __name__ == '__main__':
    unittest.main()
