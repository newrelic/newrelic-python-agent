import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.message_trace


settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance(settings.app_name)


@newrelic.api.message_trace.message_trace(library='library',
        operation='operation', destination_type='Exchange',
        destination_name='x')
def _test_function_1(message):
    pass


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_message_trace(self):
        environ = {'REQUEST_URI': '/message_trace'}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        with transaction:
            with newrelic.api.message_trace.MessageTrace(
                    library='RabbitMQ', operation='Consume',
                    destination_type='Exchange', destination_name='x'):
                pass

    def test_transaction_not_running(self):
        environ = {'REQUEST_URI': '/transaction_not_running'}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)

        with newrelic.api.message_trace.MessageTrace(
                library='RabbitMQ', operation='Consume',
                destination_type='Exchange', destination_name='x'):
            pass

    def test_message_trace_decorator(self):
        environ = {'REQUEST_URI': '/message_trace_decorator'}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)

        with transaction:
            _test_function_1('hello kitty')

    def test_message_trace_decorator_error(self):
        environ = {'REQUEST_URI': '/message_trace_decorator_error'}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)

        raises = False
        with transaction:
            try:
                _test_function_1('meow', None)
            except TypeError:
                raises = True
        assert raises

    def test_message_trace_decorator_no_transaction(self):
        _test_function_1('hello kitty')

    def test_segment_parameters_enabled(self):
        environ = {'REQUEST_URI': '/message_trace'}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        transaction.settings.message_tracer.segment_parameters_enabled = True
        params = {'cats': 'meow', 'dogs': 'wruff'}
        with transaction:
            with newrelic.api.message_trace.MessageTrace(
                    library='RabbitMQ', operation='Consume',
                    destination_type='Exchange', destination_name='x',
                    params=params) as mt:
                assert mt.params == params

    def test_segment_parameters_disabled(self):
        environ = {'REQUEST_URI': '/message_trace'}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)
        transaction.settings.message_tracer.segment_parameters_enabled = False
        params = {'cats': 'meow', 'dogs': 'wruff'}
        with transaction:
            with newrelic.api.message_trace.MessageTrace(
                    library='RabbitMQ', operation='Consume',
                    destination_type='Exchange', destination_name='x',
                    params=params) as mt:
                assert not mt.params

    # regression, see PYTHON-2844
    def test_message_trace_stopped(self):
        environ = {"REQUEST_URI": "/external_trace"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
            application, environ)
        transaction.stop_recording()

        with transaction:
            with newrelic.api.message_trace.MessageTrace(
                    library='RabbitMQ', operation='Consume',
                    destination_type='Exchange', destination_name='x'):
                pass

    def test_unknown_kwargs_raises_exception(self):
        environ = {"REQUEST_URI": "/unknown_kwargs"}
        transaction = newrelic.api.web_transaction.WSGIWebTransaction(
                application, environ)

        with transaction:
            with self.assertRaises(KeyError):
                newrelic.api.message_trace.MessageTrace(
                        "RabbitMQ", "Consume", "Exchange", "x",
                        unknown_kwarg="foo")


if __name__ == '__main__':
    unittest.main()
