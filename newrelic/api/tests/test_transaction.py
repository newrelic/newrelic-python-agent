import json
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

    def test_accept_distributed_trace_payload_encoded(self):
        with self.transaction:
            payload = ('eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkFwcCIsImFjIjoiMjAyNjQiLC'
                'JhcCI6IjEwMTk1IiwiaWQiOiIyNjFhY2E5YmM4YWVjMzc0IiwidHIiOiIyNjF'
                'hY2E5YmM4YWVjMzc0IiwicHIiOjAuMjczMTM1OTc2NTQ0MjQ1NCwic2EiOmZh'
                'bHNlLCJ0aSI6MTUyNDAxMDIyNjYxMH19')
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_json(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            payload = json.dumps(payload)
            assert isinstance(payload, str)
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_discard_version(self):
        with self.transaction:
            payload = {
                'v': [999, 0],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_distributed_trace_payload_ignore_version(self):
        with self.transaction:
            payload = {
                'v': [0, 999],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                    'new_item': 'this field should not matter',
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result

    def test_accept_distributed_trace_payload_ignores_second_call(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.is_distributed_trace
            assert self.transaction.parent_type == 'Mobile'

            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'App',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result
            assert self.transaction.is_distributed_trace
            assert self.transaction.parent_type == 'Mobile'

    def test_accept_distributed_trace_payload_discard_accounts(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '9999999999999',  # non-trusted account
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result

    def test_accept_distributed_trace_payload_priority_found(self):
        with self.transaction:
            priority = 0.123456789
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                    'pr': priority
                }
            }
            original_priority = self.transaction.priority
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.priority != original_priority
            assert self.transaction.priority == priority

    def test_accept_distributed_trace_payload_priority_not_found(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            original_priority = self.transaction.priority
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.priority == original_priority

    def test_accept_distributed_trace_payload_sampled_not_found(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            original_sampled = self.transaction.sampled
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.sampled == original_sampled

    def test_accept_distributed_trace_payload_parent_grandparent_ids(self):
        with self.transaction:
            parent_id = 'parent id'
            grandparent_id = 'grandparent id'
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': grandparent_id,
                    'id': parent_id,
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.parent_id == parent_id
            assert self.transaction.grandparent_id == grandparent_id

    def test_accept_distributed_trace_payload_no_parent_grandparent_ids(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert not hasattr(self.transaction, 'parent_id')
            assert not hasattr(self.transaction, 'grandparent_id')

    def test_accept_distributed_trace_payload_trace_id(self):
        with self.transaction:
            trace_id = 'qwerty'
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': trace_id,
                    'ti': 1518469636035,
                }
            }
            assert self.transaction.trace_id != trace_id
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert result
            assert self.transaction.trace_id == trace_id

    def test_accept_distributed_trace_payload_after_create_payload(self):
        with self.transaction:
            payload = {
                'v': [0, 1],
                'd': {
                    'ty': 'Mobile',
                    'ac': '1',
                    'ap': '2827902',
                    'pa': '5e5733a911cfbc73',
                    'id': '7d3efb1b173fecfa',
                    'tr': 'd6b4ba0c3a712ca',
                    'ti': 1518469636035,
                }
            }
            self.transaction.create_distributed_tracing_payload()
            result = self.transaction.accept_distributed_trace_payload(payload)
            assert not result


if __name__ == '__main__':
    unittest.main()
