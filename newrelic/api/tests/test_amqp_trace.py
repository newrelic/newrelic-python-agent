import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.amqp_trace

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance(settings.app_name)


@newrelic.api.amqp_trace.amqp_trace(library='library',
        operation='operation', destination_name='Earth')
def _test_function_1(message):
    pass


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_amqp_trace(self):
        environ = {'REQUEST_URI': '/amqp_trace'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            with newrelic.api.amqp_trace.AmqpTrace(
                    transaction, library='RabbitMQ', operation='Consume',
                    destination_name='Earth'):
                pass

    def test_transaction_not_running(self):
        environ = {'REQUEST_URI': '/transaction_not_running'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)

        with newrelic.api.amqp_trace.AmqpTrace(
                transaction, library='RabbitMQ', operation='Consume',
                destination_name='Earth'):
            pass

    def test_amqp_trace_decorator(self):
        environ = {'REQUEST_URI': '/amqp_trace_decorator'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)

        with transaction:
            _test_function_1('hello kitty')

    def test_amqp_trace_decorator_error(self):
        environ = {'REQUEST_URI': '/amqp_trace_decorator_error'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)

        raises = False
        with transaction:
            try:
                _test_function_1('meow', None)
            except TypeError:
                raises = True
        assert raises

    def test_amqp_trace_decorator_no_transaction(self):
        _test_function_1('hello kitty')


if __name__ == '__main__':
    unittest.main()
