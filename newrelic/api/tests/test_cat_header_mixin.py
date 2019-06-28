import newrelic.tests.test_cases

from newrelic.api.application import application_instance
from newrelic.api.message_trace import MessageTrace
from newrelic.api.transaction import Transaction, current_transaction

application = application_instance()


class TestProcessResponseHeaders(newrelic.tests.test_cases.TestCase):

    def setUp(self):
        super(TestProcessResponseHeaders, self).setUp()
        self.transaction = Transaction(application)

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_process_response_headers_message_trace_with_transaction(self):
        with self.transaction:
            with MessageTrace(self.transaction, 'library', 'operation',
                    'destination_type', 'destination_name') as trace:
                trace.process_response_headers([])

    def test_process_response_headers_message_trace_without_settings(self):
        with self.transaction:
            settings = self.transaction._settings
            self.transaction._settings = None
            with MessageTrace(self.transaction, 'library', 'operation',
                    'destination_type', 'destination_name') as trace:
                trace.process_response_headers([])
            self.transaction._settings = settings

    def test_process_response_headers_message_trace_without_transaction(self):
        with MessageTrace(None, 'library', 'operation', 'destination_type',
                'destination_name') as trace:
            trace.process_response_headers([])
