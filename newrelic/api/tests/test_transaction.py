import unittest

import newrelic.api.settings

from newrelic.api.application import application_instance
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction

import newrelic.tests.test_cases

settings = newrelic.api.settings.settings()
application = application_instance()


DISTRIBUTED_TRACE_KEYS_REQUIRED = (
        'ty', 'ac', 'ap', 'id', 'tr', 'pr', 'sa', 'ti')


class TestTraceEndsAfterTransaction(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        environ = {'REQUEST_URI': '/trace_ends_after_txn'}
        self.transaction = WebTransaction(application, environ)

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_simple(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')
            trace_1.__enter__()

            trace_2 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_2.__enter__()

        assert not self.transaction.enabled
        assert trace_1.exited
        assert trace_2.exited

    def test_max_depth_exceeded(self):
        with self.transaction:
            self.transaction._settings.agent_limits.max_outstanding_traces = 3
            for i in range(4):
                trace = FunctionTrace(self.transaction,
                        'I am going to be little late, %s' % i)
                trace.__enter__()

        assert self.transaction.enabled

    def test_one_trace_exited_one_still_running(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')

            with trace_1:
                trace_2 = FunctionTrace(
                        self.transaction, 'I am going to be a little later')
                trace_2.__enter__()

        assert not self.transaction.enabled
        assert trace_1.exited
        assert trace_2.exited

    def test_siblings_not_completed(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')
            trace_1.__enter__()
            self.transaction._pop_current(trace_1)

            trace_2 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_2.__enter__()

            assert trace_1.parent == trace_2.parent

        assert not self.transaction.enabled
        assert not trace_1.exited
        assert trace_2.exited

    def test_async_children_not_completed(self):
        with self.transaction:
            trace_1 = FunctionTrace(
                    self.transaction, 'I am going to be a little late')
            trace_1.__enter__()

            trace_2 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_2.__enter__()
            self.transaction._pop_current(trace_2)

            trace_3 = FunctionTrace(
                    self.transaction, 'I am going to be a little later')
            trace_3.__enter__()
            self.transaction._pop_current(trace_3)

        assert not self.transaction.enabled
        assert trace_1.exited


class TestTransactionApis(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def setUp(self):
        environ = {'REQUEST_URI': '/transaction_apis'}
        self.transaction = WebTransaction(application, environ)

    def tearDown(self):
        if current_transaction():
            self.transaction.drop_transaction()

    def test_create_distributed_tracing_payload_text(self):
        with self.transaction:
            payload = self.transaction.create_distributed_tracing_payload()
            assert type(payload.text()) is str

    def test_create_distributed_tracing_payload_http_safe(self):
        with self.transaction:
            payload = self.transaction.create_distributed_tracing_payload()
            assert type(payload.http_safe()) is str

    def test_distributed_trace_no_referring_transaction(self):
        with self.transaction:
            payload = self.transaction.create_distributed_tracing_payload()
            assert payload['v'] == (0, 1)

            data = payload['d']

            # Check required keys
            assert all(k in data for k in DISTRIBUTED_TRACE_KEYS_REQUIRED)

            # Type is always App
            assert data['ty'] == 'App'

            # IDs should be the transaction GUID
            assert data['id'] == self.transaction.guid
            assert data['tr'] == self.transaction.guid

            # Parent should be excluded
            assert 'pa' not in data

    def test_distributed_trace_referring_transaction(self):
        with self.transaction:
            self.transaction.referring_transaction_guid = 'abcde'
            self.transaction._trace_id = 'qwerty'
            self.transaction.priority = 0.0

            payload = self.transaction.create_distributed_tracing_payload()
            assert payload['v'] == (0, 1)

            data = payload['d']

            # Type is always App
            assert data['ty'] == 'App'

            # Check required keys
            assert all(k in data for k in DISTRIBUTED_TRACE_KEYS_REQUIRED)

            # ID should be the transaction GUID
            assert data['id'] == self.transaction.guid

            # Parent data should be forwarded
            assert data['pa'] == 'abcde'
            assert data['tr'] == 'qwerty'
            assert data['pr'] == 0.0


if __name__ == '__main__':
    unittest.main()
